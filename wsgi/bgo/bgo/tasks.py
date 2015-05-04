from django.db import transaction
from django.conf import settings

import urllib.request
import json
import datetime
import threading
import traceback
import os
from string import Template


from .models import Build, Test, Task, TestResult, Results, Commit

known_tasks = ['resolve', 'build', 'builddisks', 'smoketest', 'smoketest-classic', 'smoketest-wayland', 'smoketest-timed']
known_tests = ['applicationstest', 'integrationtest']

lock = threading.Lock()

# Connect to ES
url = os.environ['BONSAI_URL']
from elasticsearch import Elasticsearch
es = Elasticsearch([url])


def fetch_tests_and_tasks_for_build(url):
    completed = None
    for testname in known_tests:
        if not is_test_exists(url, testname):
            result = create_test_for_build(testname, url)
            if result:
                completed = result
        else:
            print("Test %s for %s already exists" % (url, testname))

    for task in known_tasks:
        if not is_task_exists(url, task):
            result = create_task_for_build(task, url)
            if result:
                completed = result

            if task == 'resolve':
                sync_commits_for_build(url)
        else:
            print("Task %s for %s already exists" % (url, task))

    return completed


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

        if created:
            payload = {
                'name': testname, 'date': start_date, 'build': build,
                'duration': int(duration), 'success': success}
            print(payload)
            es.index(index="tests", doc_type='test', id=t.id, body=payload)

        add_new_generic_test(url, testname)
        return True
    except urllib.request.HTTPError as e:
        print("not a test: %s" % e)
        return None
    except ValueError as e:
        print("Malformed JSON: %s" % e)
        return None


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
                        if created:
                            payload = {
                                'component': component, 'sha': commit_sha, 'build': build,
                                'message': message, 'change_type': change_type, 'url': url}
                            print(payload)
                            es.index(index="commits", doc_type='commit', id=t.id, body=payload)
                except Exception as e:
                    print("Malformed commit record")

        return True
    except urllib.request.HTTPError as e:
        print("no commits found: %s" % e)
        return None
    except ValueError as e:
        print("Malformed JSON: %s" % e)
        return None


def create_task_for_build(taskname, url):
    print("create_task_for_build(%s, %s)" % (taskname, url))
    try:
        response = urllib.request.urlopen("%s/%s/meta.json" % (url, taskname))
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        complete = obj['complete']
        success = False
        if not complete:
            return False
        if obj['success'] is True:
            success = True
        duration = datetime.datetime.fromtimestamp(int(obj['elapsedMillis'])/1000).time()

        build_info = get_build_info_from_url(url)
        build_name = '{0:4}{1:02}{2:02}.{3}'.format(*build_info)
        build = Build.objects.filter(name__iexact=build_name)[0]
        start_date = datetime.datetime(build_info[0], build_info[1], build_info[2])
        status = ''
        if 'status' in obj.keys():
            status = obj['status'].strip()

        t, created = Task.objects.get_or_create(
            build=build, name=taskname, start_date=start_date,
            duration=duration, success=success, status=status)
        if created:
            sec = datetime.timedelta(minutes=duration.minute, seconds=duration.second).seconds
            payload = {
                'name': taskname, 'date': start_date, 'build': build.id,
                'duration': sec, 'success': success}
            print(payload)
            es.index(index="tests", doc_type='test', id=t.id, body=payload)
        print("task was created, success=%s" % success)
        return True
    except urllib.request.HTTPError as e:
        print("not a task: %s" % e)
        return None
    except ValueError as e:
        print("Malformed JSON: %s" % e)
        return None


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
    tmp_completed = fetch_tests_and_tasks_for_build(url)
    if tmp_completed:
        print("Build task state changed, updating build.completed")
        b.completed = tmp_completed
        b.save()

    if created:
        payload = {'name': build_name, 'date': start_date}
        print(payload)
        es.index(index="builds", doc_type='build', id=url, body=payload)

    return created


def get_sub_dirs(url, quick=False):
    print("get_sub_dirs(%s)" % url)

    print("checking build %s " % url)
    # If snapshot.json exists, add a new build
    try:
        response = urllib.request.urlopen('%s/snapshot.json' % url)
        created = add_new_build(url)
        if not created and quick:
            print("Found existing build, so stopping sync")
            return
    except urllib.request.HTTPError as e:
        print("not a build")

    print("looking for subdirs")
    subdirs = []
    try:
        response = urllib.request.urlopen('%s/index.json' % url)
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        subdirs = obj['subdirs']
        print("Got subdirs: %s" % subdirs)
        subdirs = sorted(subdirs, key=int, reverse=True)
        print("found subdirs %s" % subdirs)
    except (urllib.request.HTTPError, ValueError) as e:
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
            if created:
                payload = {
                    'name': name, 'test': test.id, 'component': component, 'result': result[value]}
                print(payload)
                es.index(index="test_results", doc_type='test_result', id=tr.id, body=payload)

        test.success = total_success
        test.save()
    except urllib.request.HTTPError as e:
        print("not a test: %s" % e)
        test.success = False
    except ValueError as e:
        print("Malformed JSON: %s" % e)
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
    try:
        obj = json.loads(str_response)
    except ValueError as e:
        print("Malformed JSON: %s" % e)
        return

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

    try:
        obj = json.loads(str_response)
    except ValueError as e:
        print("Malformed JSON: %s" % e)
        return

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
        if created:
            payload = {
                'name': app['id'], 'test': test.id, 'component': 'Applications', 'result': result[app['state']]}
            print(payload)
            es.index(index="test_results", doc_type='test_result', id=tr.id, body=payload)
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


def get_buildlist():
    return Build.objects.distinct().order_by('-start_date', '-build_no')


def sync_full():
    lock.acquire()
    try:
        get_sub_dirs('%s/builds' % settings.BGO_URL, quick=False)
    except Exception:
        message = traceback.format_exc().splitlines()
        print('sync_quick: Error: %s' % message)
    finally:
        lock.release()


def sync_quick():
    lock.acquire()
    try:
        get_sub_dirs('%s/builds' % settings.BGO_URL, quick=True)
    except Exception:
        message = traceback.format_exc().splitlines()
        print('sync_quick: Error: %s' % message)
    finally:
        lock.release()


def sync_builds_date(year, month=None, day=None):
    start_url = None
    if month:
        if day:
            start_url = '%s/builds/%s/%s/%s' % (settings.BGO_URL, year, month, day)
        else:
            start_url = '%s/builds/%s/%s' % (settings.BGO_URL, year, month)
    else:
        start_url = '%s/builds/%s' % (settings.BGO_URL, year)
    print("Syncing builds starting from '%s'" % start_url)
    get_sub_dirs(start_url)


def sync_build(year, month, day, build_no):
    buildname = '{0:4}{1:02}{2:02}.{3}'.format(int(year), int(month), int(day), int(build_no))

    print("Syncing build '%s'" % buildname)
    build_url = "%s/builds/%s/%s/%s/%s" % (settings.BGO_URL, year, month, day, build_no)
    print(build_url)


def sync_test(year, month, day, build_no, test_name):
    buildname = '{0:4}{1:02}{2:02}.{3}'.format(int(year), int(month), int(day), int(build_no))
    print("Syncing test '%s' from build %s" % (test_name, buildname))

    build_url = "%s/builds/%s/%s/%s/%s" % (settings.BGO_URL, year, month, day, build_no)
    if is_test_exists(build_url, test_name):
        add_new_generic_test(build_url, test_name)