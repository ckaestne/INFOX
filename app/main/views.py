from flask import g, jsonify, render_template, redirect, url_for, current_app, abort, flash, request, make_response
from flask_login import login_required, current_user
from datetime import datetime

from . import main
from .forms import *
from ..models import *

from ..analyse import analyser
from ..analyse import fork_comparer
from ..decorators import admin_required, permission_required

from ..auth.views import get_user_repo_list, get_upperstream_repo


#------------------------------------------------------------------
def db_find_project(project_name):
    return Project.objects(project_name=project_name).first()


def db_approximate_find_project_project_name(project_name):
    _exact_project = db_find_project(project_name)
    if _exact_project:
        return _exact_project
    else:
        return Project.objects(project_name__endswith=project_name).first()


def db_add_project(project_name):
    if not db_find_project(project_name):
        analyser.start(project_name, current_user.github_access_token)
        return True
    else:
        return False


def db_delete_project(project_name):
    Project.objects(project_name=project_name).delete()
    ProjectFork.objects(project_name=project_name).delete()
    ChangedFile.objects(project_name=project_name).delete()


def db_followed_project(project_name):
    User.objects(username=current_user.username).update_one(push__followed_projects=project_name)
    # Update project followed time
    # User.objects(username=current_user.username).update(push__followed_projects_time=(project_name, datetime.utcnow()))

#------------------------------------------------------------------

@main.route('/', methods=['GET', 'POST'])
def start():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return redirect(url_for('main.welcome'))


@main.route('/welcome', methods=['GET', 'POST'])
def welcome():
    return render_template('welcome.html')


@main.route('/compare_forks', methods=['GET', 'POST'])
def compare_forks():
    """ Compare two forks by Key words
    """
    form = CompareForkForm()
    if form.validate_on_submit():
        return redirect(url_for('main.compare_forks', form=form, fork1=form.fork1.data, fork2=form.fork2.data))

    _fork1_name = request.args.get("fork1")
    _fork2_name = request.args.get("fork2")
    if _fork1_name and _fork2_name:
        _fork1 = ProjectFork.objects(fork_name=_fork1_name).first()
        _fork2 = ProjectFork.objects(fork_name=_fork2_name).first()
        if _fork1 and _fork2:
            _common_files = fork_comparer.compare_on_files(_fork1, _fork2)
            _common_words = fork_comparer.compare_on_key_words(_fork1, _fork2)
            return render_template('compare_forks.html', form=form, common_files=_common_files, common_words=_common_words)
        else:
            if _fork1 is None:
                flash('(%s) is not found!' % form.fork1.data)
            if _fork2 is None:
                flash('(%s) is not found!' % form.fork2.data)
            return redirect(url_for('main.compare_fork'))
    return render_template('compare_forks.html', form=form)


@main.route('/load_from_github', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADD)
def load_from_github():
    class ProjectSelection(FlaskForm):
        pass
    
    sync_button = SyncButton()
    if sync_button.validate_on_submit():
        return redirect(url_for('main.sync'))
    
    if current_user.owned_repo_sync_time is not None:
        _ownered_project = list(current_user.owned_repo.items())
    else:
        return redirect(url_for('main.sync'))

    for project in _ownered_project:
        setattr(ProjectSelection, project[0], BooleanField(project[1]))
    setattr(ProjectSelection, 'button_submit', SubmitField('Confirm'))
    form = ProjectSelection()
    if form.validate_on_submit():
        for field in form:
            if field.type == "BooleanField" and field.data:
                db_add_project(field.id)
                db_followed_project(field.id)
        flash('Add & Follow successfully!')
        return redirect(url_for('main.index'))
    return render_template('load_from_github.html', form=form, sync_button=sync_button)

@main.route('/sync', methods=['GET', 'POST'])
@login_required
def sync():
    _ownered_project = []
    _tmp_project_list = get_user_repo_list(current_user.username)
    for project in _tmp_project_list:
        _ownered_project.append((project, project))
        # Add upperstream_repo
        upperstream_repo = get_upperstream_repo(project)
        if upperstream_repo is not None:
            _ownered_project.append((upperstream_repo, upperstream_repo + "(Upperstream of %s)" % project))
    User.objects(username=current_user.username).update_one(set__owned_repo_sync_time=datetime.utcnow())
    User.objects(username=current_user.username).update_one(set__owned_repo=dict(_ownered_project))
    flash('Sync with Github successfully!')
    return redirect(url_for('main.load_from_github'))

@main.route('/guide', methods=['GET', 'POST'])
@login_required
def guide():
    return render_template('guide.html')

@main.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    _search_form = SearchProjectForm()
    if _search_form.validate_on_submit():
        _find_result = db_approximate_find_project_project_name(_input)
        if _find_result:
            # TODO(make sure user to follow)
            db_followed_project(_find_result.project_name)
            flash('The Project (%s) is followed successfully!' % _find_result.project_name)
            return redirect(url_for('main.project_overview', project_name=_find_result.project_name))
        else:
            # TODO(not in our database, to add)
            flash('The Project (%s) is not be in our database. Do you want to add it?' % _input)

            return redirect(url_for('main.index'))


    project_list = Project.objects(
        project_name__in=current_user.followed_projects)
    
    if len(project_list) == 0:
        return redirect(url_for('main.guide'))
    
    return render_template('index.html', projects=project_list, search_form=_search_form)


@main.route('/project/<path:project_name>', methods=['GET', 'POST'])
def project_overview(project_name):
    """ Overview of the project
        Args:
            project_name
    """
    if not db_find_project(project_name):
        abort(404)

    _project = Project.objects(project_name=project_name).first()
    _forks = ProjectFork.objects(project_name=project_name, file_list__ne=[])
    _changed_files = ChangedFile.objects(project_name=project_name)
    _all_changed_files = {}
    for file in _changed_files:
        _all_changed_files[(file.fork_name, file.file_name)] = file
    
    return render_template('project_overview.html', project=_project, forks=_forks, all_changed_files=_all_changed_files)

@main.route('/followed_project/<path:project_name>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.FOLLOW)
def followed_project(project_name):
    db_followed_project(project_name)
    flash('Followed Project %s successfully!' % project_name) 
    return redirect(url_for('main.find_repos'))


@main.route('/unfollowed_project/<path:project_name>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.FOLLOW)
def unfollowed_project(project_name):
    User.objects(username=current_user.username).update_one(
        pull__followed_projects=project_name)
    return redirect(url_for('main.index'))

@main.route('/find_repos', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADD)
def find_repos():
    form = AddProjectForm()
    if form.validate_on_submit():
        _input = form.project_name.data
        if db_find_project(_input) is not None:
            db_followed_project(_input)
            flash('The Project (%s) is already in INFOX. Followed successfully!' % _input)
        else:
            exists = analyser.start(_input, current_user.github_access_token)
            if exists:
                db_followed_project(_input)
                flash('The Project (%s) just starts loading into INFOX. Please wait.' % _input)
            else:
                flash('Not found!')

    if current_user.is_authenticated:
        project_list = Project.objects(
            project_name__nin=current_user.followed_projects)
    else:
        project_list = Project.objects

    page = request.args.get('page', 1, type=int)  # default is 1st page
    pagination = project_list.order_by('-fork_number').paginate(page=page, per_page=current_app.config['SHOW_NUMBER_FOR_PAGE'])
    projects = pagination.items
    return render_template('find_repos.html', form=form, projects=projects, pagination=pagination)


@main.route('/about')
def about():
    """About Page
    """
    form = FeedbackForm()
    if form.validate_on_submit():
        flash('Feedback received successfully!')
        print(form.feedback.data)
        return redirect(url_for('main.about'))
    return render_template('about.html', form=form)

# ---------------- Following is all admin required. ----------------

@main.route('/admin_manage')
@login_required
@admin_required
def admin_manage():
    _projects = Project.objects()
    _users = User.objects()
    return render_template('admin_manage.html', projects=_projects, users=_users)


@main.route('/project_refresh/<path:project_name>', methods=['GET', 'POST'])
@login_required
@admin_required
def project_refresh(project_name):
    """ Refresh the specfic project.
    """
    if not db_find_project(project_name):
        abort(404)
    analyser.start(project_name, current_user.github_access_token)
    return redirect(url_for('main.admin_manage'))

@main.route('/refresh_all', methods=['GET', 'POST'])
@login_required
@admin_required
def project_refresh_all():
    """ Refresh all the project.
    """
    project_list = Project.objects()
    analyser.current_analysing = set()
    for project in project_list:
        analyser.start(project.project_name, current_user.github_access_token)
    flash('refresh all successfully!')
    return redirect(url_for('main.admin_manage'))


@main.route('/delete_project/<path:project_name>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_project(project_name):
    db_delete_project(project_name)
    flash('The project (%s) is deleted!' % project_name) 
    return redirect(url_for('main.admin_manage'))


@main.route('/delete_user/<username>')
@login_required
@admin_required
def delete_user(username):
    User.objects(username=username).delete()
    flash('User (%s) is deleted!' % username)
    return redirect(url_for('main.admin_manage'))


@main.route('/_fork_edit_tag', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADD)
def _fork_edit_tag():
    _full_name = request.args.get('full_name')
    _tag = request.args.get('tag')
    _oper = request.args.get('oper')
    # print(_full_name, _tag, _oper)
    if _oper == 'delete':
        ProjectFork.objects(full_name=_full_name).update_one(pull__tags=_tag)
    elif _oper == 'add':
        ProjectFork.objects(full_name=_full_name).update_one(push__tags=_tag)
    elif _oper == 'clear':
        ProjectFork.objects(full_name=_full_name).update_one(set__tags=[])
    return jsonify(tags=ProjectFork.objects(full_name=_full_name).first().tags)

@main.route('/_get_familar_fork', methods=['GET', 'POST'])
def _get_familar_fork():
    _full_name = request.args.get('full_name')
    print(_full_name)
    if _full_name is not None:
        _fork = ProjectFork.objects(full_name=_full_name).first()
        if _fork is None:
            return None
        _fork_list = ProjectFork.objects(project_name=_fork.project_name)
        _result = fork_comparer.get_familiar_fork(_fork_list, _fork)
        return jsonify(result=_result)
    else:
        return None


@main.route('/_get_predict_tag', methods=['GET', 'POST'])
def _get_predict_tag():
    _full_name = request.args.get('full_name')
    _tag_list = ["merge", "update", "fix", "add", "branch", "pull", "request", "update", "version", "readme", "master", "change", "delete", "release", "remote", "track", "test", "remove", "patch", "configuration", "upstream", "support", "missing", "move", "conflict", "config"]
    _tag_value = dict([(x, 0.0) for x in _tag_list])
    if _full_name is None:
        return None

    _fork = ProjectFork.objects(full_name=_full_name).first()
    if _fork is None:
        return None

    for commit in _fork.commit_list:
        for tag in _tag_list:
            _tag_value[tag] += commit["title"].lower().count(tag) * 3 + commit["description"].lower().count(tag)

    _sorted_tag = [(x,y) for x, y in sorted(_tag_value.items(), key=lambda x: x[1], reverse=True)]
    _sorted_tag = [x for x, y in filter(lambda x: x[1] > 0, _sorted_tag)]
    return jsonify(result=_sorted_tag)

"""
# ----------------------------  use for test ------------------------
@main.route('/test', methods=['GET', 'POST'])
def test():
    from ..analyse.util import word_extractor
    fork_list = ProjectFork.objects()
    s = ""
    for fork in fork_list:
        for commit in fork.commit_list:
            s+=commit["title"] + "\n"
            s+=commit["description"] + "\n"
    return jsonify(word_extractor.get_top_words_from_text(s, 50))

from ..email import send_mail

@main.route('/test2', methods=['GET', 'POST'])
def test2():
    send_mail('fancycoder0@gmail.com','test', 'email.html')
    return 'hello'
"""
