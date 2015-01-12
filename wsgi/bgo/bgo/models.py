from django.db import models


class Results:
    NOTSTARTED = 0
    PASSED = 1
    FAILED = 2
    SKIPPED = 3


class Build(models.Model):
    name = models.CharField(max_length=200)
    build_no = models.IntegerField(default=0)
    start_date = models.DateTimeField()
    completed = models.BooleanField(default=1)


class Test(models.Model):
    build = models.ForeignKey(Build)
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    duration = models.IntegerField(default=0)
    results = models.IntegerField(default=Results.NOTSTARTED)
    success = models.BooleanField(default=1)


class TestResult(models.Model):
    test = models.ForeignKey(Test)
    name = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    result = models.IntegerField(default=Results.NOTSTARTED)

    def build_artifacts_url(self):
        root = 'http://build.gnome.org/continuous/buildmaster/builds'
        build = self.test.build
        result = '{0}/{1:4}/{2:02}/{3:02}/{4}'.format(
            root, build.start_date.year, build.start_date.month,
            build.start_date.day, build.build_no)
        if self.test.name == 'integrationtest':
            result = '%s/%s/work-gnome-continuous-x86_64-runtime/installed-test-results/' % (
                result, self.test.name)
            result = '%s/%s_%s' % (result, self.component, self.name)
        return result
