from django.db import models


class Results:
    NOTSTARTED = 0
    PASSED = 1
    FAILED = 2
    SKIPPED = 3


class Build(models.Model):
    name = models.CharField(max_length=200)
    build_no = models.IntegerField(default=0)
    start_date = models.DateTimeField(default=None)
    completed = models.BooleanField(default=1)

    def build_url(self):
        root = 'http://build.gnome.org/continuous/buildmaster/builds'
        return '{0}/{1:4}/{2:02}/{3:02}/{4}'.format(
            root, self.start_date.year, self.start_date.month,
            self.start_date.day, self.build_no)


class Task(models.Model):
    build = models.ForeignKey(Build)
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField(default=None)
    duration = models.TimeField(default=None)
    success = models.BooleanField(default=1)

    tasknames = {
        "resolve": "Resolve",
        "build": "Build",
        "builddisks": "Image building",
        "smoketest": "Smoke test",
        "smoketest-classic": "Classic mode",
        "smoketest-wayland": "Wayland"}

    def nice_name(self):
        if self.name in self.tasknames.keys():
            return self.tasknames[self.name]
        else:
            return self.name

    def screenshot(self):
        if 'smoketest' not in self.name:
            return
        root = self.build.build_url()
        return '%s/%s/work-gnome-continuous-x86_64-runtime/screenshot-final.png' % (root, self.name)


class Commit(models.Model):
    build = models.ForeignKey(Build)
    component = models.CharField(max_length=200)
    url = models.CharField(max_length=200)
    sha = models.CharField(max_length=200)
    message = models.CharField(max_length=200)
    change_type = models.CharField(max_length=200)


class Test(models.Model):
    build = models.ForeignKey(Build)
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    duration = models.TimeField(default=None)
    results = models.IntegerField(default=Results.NOTSTARTED)
    success = models.BooleanField(default=1)

    testnames = {
        "applicationstest": "Applications test",
        "integrationtest": "Installed tests"}

    def nice_name(self):
        if self.name in self.testnames.keys():
            return self.testnames[self.name]
        else:
            return self.name

    def build_url(self):
        root = self.build.build_url()
        return '%s/%s' % (root, self.name)


class TestResult(models.Model):
    test = models.ForeignKey(Test)
    name = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    result = models.IntegerField(default=Results.NOTSTARTED)

    def build_artifacts_url(self):
        root = self.test.build_url()
        if self.test.name == 'integrationtest':
            result = '%s/%s/work-gnome-continuous-x86_64-runtime/installed-test-results/' % (
                root, self.test.name)
            result = '%s/%s_%s' % (result, self.component, self.name)
        else:
            result = '%s/%s/icons/%s.png' % (root, self.test.name, self.name)
        return result
