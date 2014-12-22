from django.db import models


class Results:
    NOTSTARTED = 0
    PASSED = 1
    FAILED = 2
    SKIPPED = 3


class Build(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField('date published')


class Test(models.Model):
    build = models.ForeignKey(Build)
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField('date published')
    duration = models.IntegerField(default=0)
    results = models.IntegerField(default=Results.NOTSTARTED)
    screenshot = models.URLField(max_length=200)


class TestResult(models.Model):
    test = models.ForeignKey(Test)
    name = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    result = models.IntegerField(default=Results.NOTSTARTED)
