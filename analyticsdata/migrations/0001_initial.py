# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CourseUserActivityByWeek'
        db.create_table('course_user_activity_by_week', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('from_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('to_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('action', self.gf('django.db.models.fields.IntegerField')()),
            ('count', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('analyticsdata', ['CourseUserActivityByWeek'])


    def backwards(self, orm):
        # Deleting model 'CourseUserActivityByWeek'
        db.delete_table('course_user_activity_by_week')


    models = {
        'analyticsdata.courseuseractivitybyweek': {
            'Meta': {'object_name': 'CourseUserActivityByWeek', 'db_table': "'course_user_activity_by_week'"},
            'action': ('django.db.models.fields.IntegerField', [], {}),
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'from_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_date': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['analyticsdata']