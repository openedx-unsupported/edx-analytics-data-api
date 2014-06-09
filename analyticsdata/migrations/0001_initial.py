# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CourseActivityLastWeek'
        db.create_table('course_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('interval_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('interval_end', self.gf('django.db.models.fields.DateTimeField')()),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('count', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('analyticsdata', ['CourseActivityLastWeek'])


    def backwards(self, orm):
        # Deleting model 'CourseActivityLastWeek'
        db.delete_table('course_activity')


    models = {
        'analyticsdata.courseactivitylastweek': {
            'Meta': {'object_name': 'CourseActivityLastWeek', 'db_table': "'course_activity'"},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval_end': ('django.db.models.fields.DateTimeField', [], {}),
            'interval_start': ('django.db.models.fields.DateTimeField', [], {}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        }
    }

    complete_apps = ['analyticsdata']