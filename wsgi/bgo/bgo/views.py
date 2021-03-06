from django.shortcuts import get_object_or_404
from django.views import generic
from django.db.models import Count
from django.core.paginator import InvalidPage

from bgo.bgo.models import Build, Test, TestResult, Task, Commit
from bgo.bgo.tasks import get_buildlist


class BuildsListView(generic.ListView):
    template_name = 'home/build_list.html'
    context_object_name = 'buildslist'
    model = Build
    paginate_by = 15

    def get_paginated_queryset(self):
        (paginator, page, buildlist, is_paginated) = self.paginate_queryset(get_buildlist(), 15)
        return (paginator, buildlist)

    def get_queryset(self):
        return get_buildlist()

    def get_context_data(self, **kwargs):
        context = super(BuildsListView, self).get_context_data(**kwargs)
        (paginator, buildlist) = self.get_paginated_queryset()
        current_page = self.request.REQUEST.get('page')  # or self.request.session['page']
        try:
            current_page = paginator.validate_number(int(current_page))
        except (InvalidPage, TypeError):
            current_page = 1
        # Save page in session
        self.request.session['page'] = current_page
        context['page_obj'] = paginator.page(current_page)
        context['buildslist'] = buildlist
        context['remainder'] = '?page=%d' % current_page
        return context


class BuildDetailView(BuildsListView):
    template_name = 'home/build_detail.html'
    paginate_by = None

    def get_queryset(self):
        self.build = get_object_or_404(Build, name=self.args[0])
        self.tests = Test.objects.filter(build=self.build)
        self.tasks = Task.objects.filter(build=self.build).order_by('start_date')
        self.task_names = self.tasks.values_list('name', flat=True)
        self.commits = Commit.objects.filter(build=self.build)

        self.tests = self.tests.annotate(total=Count('testresult__result'))
        # Magic trick to calculate passed/failed/skipped as Django doesn't like filtering
        results = TestResult.objects.all().filter(test__in=self.tests)
        results = results.values('test', 'result').annotate(abs=Count('pk'))
        for test in self.tests:
            for (var, result_id) in [("passed", 1), ("failed", 2), ("skipped", 3)]:
                try:
                    value = [x['abs'] for x in results if x['test'] == test.pk and x['result'] == result_id][0]
                    setattr(test, var, value)
                except:
                    pass
        return self.tests

    def get_context_data(self, **kwargs):
        context = super(BuildDetailView, self).get_context_data(**kwargs)
        context['build'] = self.build
        context['tasks'] = self.tasks
        context['task_names'] = self.task_names
        context['commits'] = self.commits
        return context


class IntegrationTestDetailView(BuildsListView):
    template_name = 'home/integrationtest_detail.html'
    paginate_by = None

    def get_queryset(self):
        self.build = get_object_or_404(Build, name=self.args[0])
        self.test = get_object_or_404(Test, build=self.build, name='integrationtest')

        testresult_filter = TestResult.objects.filter(test=self.test)
        return testresult_filter.order_by('component')

    def get_context_data(self, **kwargs):
        context = super(IntegrationTestDetailView, self).get_context_data(**kwargs)
        context['build'] = self.build
        context['test'] = self.test
        return context


class ApplicationsTestDetailView(BuildsListView):
    template_name = 'home/applicationtest_detail.html'
    paginate_by = None

    def get_queryset(self):
        self.build = get_object_or_404(Build, name=self.args[0])
        self.test = get_object_or_404(Test, build=self.build, name='applicationstest')

        testresult_filter = TestResult.objects.filter(test=self.test)
        return testresult_filter.order_by('name')

    def get_context_data(self, **kwargs):
        context = super(ApplicationsTestDetailView, self).get_context_data(**kwargs)
        context['build'] = self.build
        context['test'] = self.test
        return context


class TestHistoryView(BuildsListView):
    template_name = 'home/test_history.html'
    paginate_by = None

    def get_queryset(self):
        self.test = get_object_or_404(TestResult, id=self.args[0])
        self.testname = self.test.name
        self.testcomponent = self.test.component
        return TestResult.objects.filter(name=self.testname, component=self.testcomponent).\
            order_by('-test__start_date', '-test__build__build_no')

    def get_context_data(self, **kwargs):
        context = super(TestHistoryView, self).get_context_data(**kwargs)
        context['testname'] = self.testname
        context['testcomponent'] = self.testcomponent
        return context


class ComponentList(BuildsListView):
    template_name = 'home/components.html'
    paginate_by = None

    def get_queryset(self):
        self.components = sorted(TestResult.objects.values_list('component', flat=True).distinct())
        return []

    def get_context_data(self, **kwargs):
        context = super(ComponentList, self).get_context_data(**kwargs)
        context['components'] = self.components
        return context


class ComponentDetailView(BuildsListView):
    template_name = 'home/component_details.html'
    paginate_by = None

    def get_queryset(self):
        self.component = self.args[0]
        self.testresults = TestResult.objects.filter(component=self.component).\
            order_by('-test__start_date', 'test__build__build_no')
        buildresults = self.testresults.values_list('test__build__name', 'result')
        self.builds = []
        for x in buildresults:
            self.builds.append({'name': x[0]})

        for build in self.builds:
            build_results = [x[1] for x in buildresults if x[0] == build['name']]
            for (name, id) in [('passed', 1), ('failed', 2), ('skipped', 3)]:
                build[name] = build_results.count(id)
        return []

    def get_context_data(self, **kwargs):
        context = super(ComponentDetailView, self).get_context_data(**kwargs)
        context['builds'] = self.builds
        context['component'] = self.component
        return context
