from django.db import transaction

import urllib.request
import json
import datetime
from string import Template


from bgo.models import Build, Test, Task, TestResult, Results, Commit

known_tasks = ['resolve', 'build', 'builddisks']
known_tests = ['applicationstest', 'integrationtest']


def fetch_tests_and_tasks_for_build(url):
    completed = False
    for testname in known_tests:
        if not is_test_exists(url, testname):
            result = create_test_for_build(testname, url)
            completed &= result
        else:
            print("Test %s for %s already exists" % (url, testname))

    for task in known_tasks:
        if not is_task_exists(url, task):
            result = create_task_for_build(task, url)
            completed &= result

            if task == 'resolve':
                result = sync_commits_for_build(url)
                completed &= result
        else:
            print("Task %s for %s already exists" % (url, task))


def is_test_exists(url, testname):
    if is_build_exists(url):
        build_info = get_build_info_from_url(url)
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
        return Test.objects.filter(build__name__iexact=build_name, name__iexact=testname)
    else:
        return False


def is_task_exists(url, task):
    if is_build_exists(url):
        build_info = get_build_info_from_url(url)
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
        return Task.objects.filter(build__name__iexact=build_name, name__iexact=task)
    else:
        return False


def create_test_for_build(testname, url):
    print("create_test_for_build(%s, %s)" % (testname, url))
    try:
        response = urllib.request.urlopen("%s/%s/meta.json" % (url, testname))
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        complete = obj['complete']
        if not complete:
            return False
        if obj['success'] is True:
            success = Results.PASSED
        else:
            success = Results.FAILED
        duration = datetime.datetime.fromtimestamp(int(obj['elapsedMillis'])/1000).time()

        build_info = get_build_info_from_url(url)
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
        build = Build.objects.filter(name__iexact=build_name)[0]
        start_date = datetime.datetime(build_info[0], build_info[1], build_info[2])

        t, created = Test.objects.get_or_create(
            build=build, name=testname, start_date=start_date,
            duration=duration, success=success)
        print("test was created")

        add_new_generic_test(url, testname)
        return True
    except urllib.request.HTTPError as e:
        print("not a test: %s" % e)
        return True


def get_url_template_for_src(src):
    known_srcs = {
        'git:git://git.kernel.org/pub/scm/': 'https://git.kernel.org/cgit/$component/commit/?id=$commit',
        'git:git://anongit.freedesktop.org/': 'http://cgit.freedesktop.org/$component/commit/?id=$commit',
        'git:git://anongit.freedesktop.org/git/': 'http://cgit.freedesktop.org/$component/commit/?id=$commit',
        'git:git://git.gnome.org/': 'https://git.gnome.org/browse/$component/commit/?id=$commit',
        'git:git://github.com': 'https://github.com/$component/commit/$commit',
        'git:http://git.chromium.org/': 'http://git.chromium.org/gitweb/?p=$component;a=commit;h=$commit'
    }

    for known_src in known_srcs:
        if src.startswith(known_src):
            component = src.replace(known_src, '')
            return Template(known_srcs[known_src]).safe_substitute(dict(component=component))
    raise Exception("No known src for %s" % src)


def sync_commits_for_build(url):
    print("sync_commits_for_build(%s)" % url)
    try:
        response = urllib.request.urlopen("%s/bdiff.json" % url)
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)

        build_info = get_build_info_from_url(url)
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
        build = Build.objects.filter(name__iexact=build_name)[0]

        for change_type in ['added', 'modified', 'removed']:
            changes = obj[change_type]
            if not changes:
                continue

            for component_dict in changes:
                try:
                    component = component_dict['previous']['name']
                    url_template = get_url_template_for_src(component_dict['previous']['src'])

                    for commit_dict in component_dict['gitlog']:
                        commit_sha = commit_dict['Checksum'][:8]
                        message = commit_dict['Subject']
                        url = Template(url_template).substitute(dict(commit=commit_sha))
                        t, created = Commit.objects.get_or_create(
                            build=build, component=component, sha=commit_sha,
                            message=message, change_type=change_type, url=url)
                        print("Added commit %s" % commit_sha)
                except Exception as e:
                    print("Malformed commit record")

        return True
    except urllib.request.HTTPError as e:
        print("no commits found: %s" % e)
        return True


def create_task_for_build(taskname, url):
    print("create_task_for_build(%s, %s)" % (taskname, url))
    try:
        response = urllib.request.urlopen("%s/%s/meta.json" % (url, taskname))
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        complete = obj['complete']
        if not complete:
            return False
        if obj['success'] is True:
            success = Results.PASSED
        else:
            success = Results.FAILED
        duration = datetime.datetime.fromtimestamp(int(obj['elapsedMillis'])/1000).time()

        build_info = get_build_info_from_url(url)
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
        build = Build.objects.filter(name__iexact=build_name)[0]
        start_date = datetime.datetime(build_info[0], build_info[1], build_info[2])

        t, created = Task.objects.get_or_create(
            build=build, name=taskname, start_date=start_date,
            duration=duration, success=success)
        print("task was created")
        return True
    except urllib.request.HTTPError as e:
        print("not a task: %s" % e)
        return True


def get_build_info_from_url(url):
    split_url = url.split('/')
    try:
        year = int(split_url[-4])
        month = int(split_url[-3])
        day = int(split_url[-2])
        build_no = int(split_url[-1])
    except Exception as e:
        print("Error: %s" % e)
        return (None, None, None, None)

    return (year, month, day, build_no)


def is_build_exists(url):
    (year, month, day, build_no) = get_build_info_from_url(url)

    if year is not None:
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(year, month, day, build_no)
        return len(Build.objects.filter(name__iexact=build_name)) > 0
    else:
        return False


def add_new_build(url):
    print("add_new_build(%s)" % url)

    (year, month, day, build_no) = get_build_info_from_url(url)
    build_name = '{0:4}{1:02}{2:02}.{3}'.format(year, month, day, build_no)
    print('build name: %s' % build_name)
    start_date = datetime.datetime(year, month, day)
    print('start date: %s' % start_date)
    b, created = Build.objects.get_or_create(name=build_name, start_date=start_date, build_no=build_no)
    print("Build created")
    if created:
        print("Build created, fetching tests")
    elif not b.completed:
        print("Build is not completed, updating tests")
    else:
        print("Build is completed, skipping tests info")
    b.completed = fetch_tests_and_tasks_for_build(url)


def get_sub_dirs(url):
    print("get_sub_dirs(%s)" % url)

    print("checking build %s " % url)
    # If this build already exists, skip it
    if not is_build_exists(url):
        # If snapshot.json exists, add a new build
        try:
            response = urllib.request.urlopen('%s/snapshot.json' % url)
            add_new_build(url)
        except urllib.request.HTTPError as e:
            print("not a build")
    else:
        print("build is already added, skipping")

    print("looking for subdirs")
    subdirs = []
    try:
        response = urllib.request.urlopen('%s/index.json' % url)
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        subdirs = obj['subdirs']
        print("found subdirs %s" % subdirs)
    except urllib.request.HTTPError as e:
        return "failure: %s" % str(e)

    # Iterate over subdirs
    for subdir in subdirs:
        get_sub_dirs("%s/%s" % (url, subdir))

    return "success"


@transaction.atomic
def add_new_installed_test(url):
    print("add_new_installed_test(%s)" % url)
    build_info = get_build_info_from_url(url)
    build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
    test = Test.objects.filter(build__name__iexact=build_name, name__iexact='integrationtest')[0]
    try:
        response = urllib.request.urlopen("%s/integrationtest/installed-test-results.json" % url)
        str_response = response.readall().decode('utf-8')
        if len(str_response) == 0:
            print("Empty results, skipping")
            return

        total_success = True
        obj = json.loads(str_response)
        for key, value in obj.items():
            (component, name) = key.split('/', 1)
            result = {'failed': Results.FAILED, 'success': Results.PASSED, 'skipped': Results.SKIPPED}

            if result[value] == Results.FAILED:
                total_success = False

            tr, created = TestResult.objects.get_or_create(
                test=test, name=name, component=component, result=result[value])
            print("added test result for %s:%s - %s" % (component, name, value))

        test.success = total_success
        test.save()
    except urllib.request.HTTPError as e:
        print("not a test: %s" % e)
        test.success = False


@transaction.atomic
def add_new_application_test(url):
    print("add_new_application_test(%s)" % url)
    build_info = get_build_info_from_url(url)
    build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
    test = Test.objects.filter(build__name__iexact=build_name, name__iexact='applicationstest')[0]
    try:
        response = urllib.request.urlopen("%s/applicationstest/meta.json" % url)
    except urllib.request.HTTPError as e:
        print("not a test: %s" % e)
        return

    str_response = response.readall().decode('utf-8')
    if len(str_response) == 0:
        print("Empty meta, skipping")
        return
    obj = json.loads(str_response)

    if 'complete' not in obj.keys() or not obj['complete']:
        print("Test is in progress, skipping result parse")
        return

    success = False
    if 'success' in obj.keys() and obj['success']:
        success = True

    # Parse apps.json
    try:
        response = urllib.request.urlopen("%s/applicationstest/apps.json" % url)
    except urllib.request.HTTPError as e:
        print("no apps.json: %s" % e)
        test.success = False
        test.save()
        return

    str_response = response.readall().decode('utf-8')
    if len(str_response) == 0:
        print("Empty apps.json, skipping")
        test.success = False
        test.save()
        return
    obj = json.loads(str_response)

    if 'apps' not in obj.keys():
        print("No apps section")
        test.success = False
        test.save()
        return

    total_success = True
    apps = obj['apps']
    for app in apps:
        result = {'failed': Results.FAILED, 'timeout': Results.FAILED, 'running': Results.FAILED, 'success': Results.PASSED}

        if result[app['state']] == Results.FAILED:
            total_success = False

        tr, created = TestResult.objects.get_or_create(
            test=test, name=app['id'], component='Applications', result=result[app['state']])
        print("added test result for %s: %s" % (app['id'], app['state']))

    test.success = success and total_success
    test.save()


def add_new_generic_test(url, testname):
    if testname == 'integrationtest':
        add_new_installed_test(url)
    elif testname == 'applicationstest':
        add_new_application_test(url)
    else:
        print("Unknown test: '%s', skipping" % testname)
