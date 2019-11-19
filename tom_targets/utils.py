from django.db.models import Count

import csv
from .models import Target, TargetExtra, TargetName
from io import StringIO


# NOTE: This saves locally. To avoid this, create file buffer.
# referenced https://www.codingforentrepreneurs.com/blog/django-queryset-to-csv-files-datasets/
def export_targets(qs):
    """
    Exports all the specified targets into a csv file in folder csvTargetFiles
    NOTE: This saves locally. To avoid this, create file buffer.

    :param qs: List of targets to export
    :type qs: QuerySet

    :returns: String buffer of exported targets
    :rtype: StringIO
    """
    qs_pk = [data['id'] for data in qs]
    data_list = list(qs)
    target_fields = [field.name for field in Target._meta.get_fields()]
    target_extra_fields = list({field.key for field in TargetExtra.objects.filter(target__in=qs_pk)})
    # Gets the count of the target names for the target with the most aliases in the database
    # This is to construct enough row headers of format "name2, name3, name4, etc" for exporting aliases
    # The alias headers are then added to the set of fields for export
    max_alias_count = max([alias['count'] for alias
                           in TargetName.objects.values('target_id').annotate(count=Count('target_id'))])
    all_fields = target_fields + target_extra_fields + [f'name{index+1}' for index in range(1, max_alias_count+1)]
    for key in ['id', 'targetlist', 'dataproduct', 'observationrecord', 'reduceddatum', 'aliases', 'targetextra']:
        all_fields.remove(key)

    file_buffer = StringIO()
    writer = csv.DictWriter(file_buffer, fieldnames=all_fields)
    writer.writeheader()
    for target_data in data_list:
        extras = list(TargetExtra.objects.filter(target_id=target_data['id']))
        names = list(TargetName.objects.filter(target_id=target_data['id']))
        for e in extras:
            target_data[e.key] = e.value
        name_index = 2
        for name in names:
            target_data[f'name{str(name_index)}'] = name.name
            name_index += 1
        del target_data['id']  # do not export 'id'
        writer.writerow(target_data)
    return file_buffer


def import_targets(targets):
    """
    Imports a set of targets into the TOM and saves them to the database.

    :param targets: String buffer of targets
    :type targets: StringIO

    :returns: dictionary of successfully imported targets, as well errors
    :rtype: dict
    """
    # TODO: Replace this with an in memory iterator
    targetreader = csv.DictReader(targets, dialect=csv.excel)
    targets = []
    errors = []
    base_target_fields = [field.name for field in Target._meta.get_fields()]
    for index, row in enumerate(targetreader):
        # filter out empty values in base fields, otherwise converting empty string to float will throw error
        row = {k: v for (k, v) in row.items() if not (k in base_target_fields and not v)}
        target_extra_fields = []
        target_names = []
        target_fields = {}
        for k in row:
            # All fields starting with 'name' (e.g. name2, name3) that aren't literally 'name' will be added as
            # TargetNames
            if k != 'name' and k.startswith('name'):
                target_names.append(row[k])
            elif k not in base_target_fields:
                target_extra_fields.append((k, row[k]))
            else:
                target_fields[k] = row[k]
        for extra in target_extra_fields:
            row.pop(extra[0])
        try:
            target = Target.objects.create(**target_fields)
            for extra in target_extra_fields:
                TargetExtra.objects.create(target=target, key=extra[0], value=extra[1])
            for name in target_names:
                if name:
                    TargetName.objects.create(target=target, name=name)
            targets.append(target)
        except Exception as e:
            error = 'Error on line {0}: {1}'.format(index + 2, str(e))
            errors.append(error)

    return {'targets': targets, 'errors': errors}
