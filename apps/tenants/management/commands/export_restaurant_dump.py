import gzip
import json
import os
import subprocess
import tempfile

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.dump_export import export_from_database


class Command(BaseCommand):
    help = 'Legacy PostgreSQL dump faylını tenant JSON export-a çevirir.'

    def add_arguments(self, parser):
        parser.add_argument(
            'dump_file',
            nargs='?',
            default='data/restaurant_db_20260930.dump',
            help='pg_restore dump faylının yolu',
        )
        parser.add_argument(
            '-o', '--output',
            default='data/qonaq_baku.json.gz',
            help='Çıxış JSON (gzip) faylının yolu',
        )
        parser.add_argument(
            '--include-history',
            action='store_true',
            help='Historical order/statistics cədvəllərini də export et',
        )
        parser.add_argument(
            '--source-url',
            default=None,
            help='Artıq restore olunmuş bazanın DATABASE URL-i (dump restore atlanır)',
        )

    def handle(self, *args, **options):
        source_url = options['source_url']
        temp_db = None

        if not source_url:
            dump_path = options['dump_file']
            if not os.path.isfile(dump_path):
                raise CommandError(f'Dump faylı tapılmadı: {dump_path}')

            temp_db = 'qonaq_export_tmp'
            subprocess.run(['dropdb', '--if-exists', temp_db], check=False)
            subprocess.run(['createdb', temp_db], check=True)
            restore = subprocess.run(
                ['pg_restore', '--no-owner', '--no-acl', '-d', temp_db, dump_path],
                capture_output=True,
                text=True,
            )
            if restore.returncode not in (0, 1):
                raise CommandError(restore.stderr or 'pg_restore uğursuz oldu')

            source_url = f'postgresql:///{temp_db}'

        try:
            payload = export_from_database(
                source_url,
                include_history=options['include_history'],
            )
            model_count = sum(len(v) for v in payload['models'].values())
            output_path = options['output']
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with gzip.open(output_path, 'wt', encoding='utf-8') as handle:
                json.dump(payload, handle, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(
                f'{model_count} qeyd export edildi → {output_path}'
            ))
        finally:
            if temp_db:
                subprocess.run(['dropdb', '--if-exists', temp_db], check=False)
