from django.shortcuts import render_to_response
from django.conf import settings
from django.db import transaction

import urllib.request
import json
import datetime

from bgo.models import Build, Test, TestResult, Results

known_tests = ['applicationstest', 'integrationtest']


def fetch_tests_for_build(url):
    for testname in known_tests:
        if not is_test_exists(url, testname):
            create_test_for_build(testname, url)
        else:
            print("Test %s for %s already exists" % (url, testname))


def is_test_exists(url, testname):
    if is_build_exists(url):
        build_info = get_build_info_from_url(url)
        build_name = '%s%s%s.%s' % build_info
        return Test.objects.filter(build__name__iexact=build_name, name__iexact=testname)
    else:
        return False


def create_test_for_build(testname, url):
    print("---")
    print("create_test_for_build(%s, %s)" % (testname, url))
    try:
        response = urllib.request.urlopen("%s/%s/meta.json" % (url, testname))
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        complete = obj['complete']
        assert complete is True, "test is incomplete"
        if obj['success'] is True:
            success = Results.PASSED
        else:
            success = Results.FAILED
        duration = obj['elapsedMillis']

        build_info = get_build_info_from_url(url)
        build_name = '%s%s%s.%s' % build_info
        build = Build.objects.filter(name__iexact=build_name)[0]
        start_date = datetime.datetime(build_info[0], build_info[1], build_info[2])

        t = Test(build=build, name=testname, start_date=start_date,
                 duration=int(duration), results=success, screenshot='')
        t.save()
        print("test was created")
    except Exception as e:
        print("not a test: %s" % e)
    print("---")


def get_build_info_from_url(url):
    split_url = url.split('/')
    try:
        year = int(split_url[-4])
        month = int(split_url[-3])
        day = int(split_url[-2])
        build_no = int(split_url[-1])
    except Exception as e:
        print("Error: %s" % e)
        print("---")
        return (None, None, None, None)

    return (year, month, day, build_no)


def is_build_exists(url):
    (year, month, day, build_no) = get_build_info_from_url(url)

    if year is not None:
        build_name = '%s%s%s.%s' % (year, month, day, build_no)
        return len(Build.objects.filter(name__iexact=build_name)) > 0
    else:
        return False


def add_new_build(url):
    print("---")
    print("add_new_build(%s)" % url)

    (year, month, day, build_no) = get_build_info_from_url(url)
    build_name = '%s%s%s.%s' % (year, month, day, build_no)
    print('build name: %s' % build_name)
    start_date = datetime.datetime(year, month, day)
    print('start date: %s' % start_date)
    b = Build(name=build_name, start_date=start_date)
    b.save()
    print("Build created")
    print("---")


def get_sub_dirs(url):
    print("---")
    print("get_sub_dirs(%s)" % url)

    print("checking build %s " % url)
    # If this build already exists, skip it
    if not is_build_exists(url):
        # If snapshot.json exists, add a new build
        try:
            response = urllib.request.urlopen('%s/snapshot.json' % url)
            add_new_build(url)
        except Exception as e:
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
    except Exception as e:
        return "failure: %s" % str(e)

    # Iterate over subdirs
    #for (i, subdir) in enumerate(subdirs):
    #    if i < 3:
    #        get_sub_dirs("%s/%s" % (url, subdir))
    for subdir in subdirs:
        get_sub_dirs("%s/%s" % (url, subdir))

    return "success"


@transaction.atomic
def add_new_installed_test(url):
    print("---")
    print("add_new_installed_test(url)")
    build_info = get_build_info_from_url(url)
    build_name = '%s%s%s.%s' % build_info
    test = Test.objects.filter(build__name__iexact=build_name, name__iexact='integrationtest')[0]
    try:
        response = urllib.request.urlopen("%s/integrationtest/installed-test-results.json" % url)
        str_response = response.readall().decode('utf-8')
        obj = json.loads(str_response)
        for key, value in obj.items():
            (component, name) = key.split('/', 1)
            result = {'failed': Results.FAILED, 'success': Results.PASSED, 'skipped': Results.SKIPPED}
            tr = TestResult(test=test, name=name, component=component, result=result[value])
            tr.save()
            print("added test result for %s:%s - %s" % (component, name, value))
    except urllib.request.HTTPError as e:
        print("not a test: %s" % e)
    print("---")


def add_new_generic_test(url, testname):
    if testname == 'integrationtest':
        add_new_installed_test(url)


def sync_buildlist(request):
    bgo_url = settings.BGO_URL

    state = get_sub_dirs('%s/builds' % bgo_url)

    return render_to_response('home/syncstatus.html',
                              {'state': state, 'target': "builds list"})


def sync_build(request, year, month, day, build_no):
    buildname = "%s%s%s.%s" % (year, month, day, build_no)
    state = "success"

    print("Syncing build '%s'" % buildname)
    bgo_url = settings.BGO_URL
    build_url = "%s/builds/%s/%s/%s/%s" % (bgo_url, year, month, day, build_no)
    if not is_build_exists(build_url):
        state = "no such build"
    else:
        fetch_tests_for_build(build_url)

    return render_to_response('home/syncstatus.html',
                              {'state': state, 'target': "build %s" % buildname})


def sync_test(request, year, month, day, build_no, test_name):
    buildname = "%s%s%s.%s" % (year, month, day, build_no)
    print("Syncing test '%s' from build %s" % (test_name, buildname))
    state = "success"

    bgo_url = settings.BGO_URL
    build_url = "%s/builds/%s/%s/%s/%s" % (bgo_url, year, month, day, build_no)
    if not is_test_exists(build_url, test_name):
        state = "no such test"
    else:
        add_new_generic_test(build_url, test_name)
    return render_to_response('home/syncstatus.html',
                              {'state': state, 'target': "build %s test %s" % (buildname, test_name)})
