import subprocess, json, shutil, stat, os, errno, sys
import urllib.request as requests
import urllib.error as RequestErrors
import urllib.parse as urlParse

TOTAL_STEP = 7
API_URL = 'https://gitlab.com/api/v4/'

API_TOKEN = None
GROUP_NAME = None
MAIN_REPO = None


def readArgs():
    """Read console args and instatiate global variable with it"""
    global API_TOKEN, GROUP_NAME, MAIN_REPO
    try:
        args = sys.argv
        if args[1] == '--help' or args[1] == '-h':
            displayHelp()

        else:
            API_TOKEN=args[1]
            GROUP_NAME=args[2]
            MAIN_REPO=args[3]

    except IndexError as e:
        print("ERR: No argument given use '-h' to see help")
        exit()


def displayHelp():
    """Show help text"""
    print(
    """
    usage: 
        migrate_to_one_project.py [-h] api-token group-name main-repo

    required arguments:
        api-token               Token mandatory to use gitlab API see gitlab documentation 
                                at https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html
        group-name              Name of the group where all projects are.
        main-repo               The repository where all the other group's projects will be pushed as 
                                branches
    
    optional arguments:
        -h, --help              show this help message and exit
    """
    )
    exit()


def handleRemoveReadonly(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def gitlab_get(urlPath ,urlParams={}):
    """
    Get data from gitlab API
  
    Parameters: 
    urlPath (str): url endpoint path
    urlParams (dict) : params as {"key": "value"}

    Returns: 
    dict: Json response
    """
    try:
        urlParams["access_token"] = API_TOKEN
        url = "{}{}/?{}".format(API_URL, urlPath, urlParse.urlencode(urlParams))
        return json.loads(requests.urlopen(url).read())

    except RequestErrors.HTTPError as e :
        print("ERR {}: Something with gitlab API went wrong : {}".format(e.code, e.reason))
    except RequestErrors.URLError as e : 
        print("ERR: The given URL is wrong : {}".format(e.reason))


def gitlab_post(urlPath, urlParams={}):
    """
    Get data to gitlab API
  
    Parameters: 
        urlPath (str): url endpoint path
        urlParams (dict) : params as {"key": "value"}

    Returns: 
        dict: Json response
    """
    try:
        url = "{}{}/?{}".format(API_URL, urlPath, urlParse.urlencode(urlParams))
        query = requests.Request(url)
        query.add_header('PRIVATE-TOKEN', API_TOKEN)
        return json.loads(requests.urlopen(query).read())
    
    except RequestErrors.HTTPError as e :
        print("ERR {}: Something with gitlab API went wrong : {}".format(e.code, e.reason))
    except RequestErrors.URLError as e : 
        print("ERR: The given URL is wrong : {}".format(e.reason))


def progress(count, total, status=''):
    """
    Show a progress bar in console

    Author:
        Vladimir Ignatev
    
    See:
        https://gist.github.com/vladignatyev/06860ec2040cb497f0f3

    LICENCE:
        The MIT License (MIT)
        Copyright (c) 2016 Vladimir Ignatev
        
        Permission is hereby granted, free of charge, to any person obtaining 
        a copy of this software and associated documentation files (the "Software"), 
        to deal in the Software without restriction, including without limitation 
        the rights to use, copy, modify, merge, publish, distribute, sublicense, 
        and/or sell copies of the Software, and to permit persons to whom the Software 
        is furnished to do so, subject to the following conditions:
        
        The above copyright notice and this permission notice shall be included 
        in all copies or substantial portions of the Software.
        
        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
        INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
        PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
        FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
        OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
        OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    sys.stdout.flush()  # As suggested by Rom Ruben (see: http://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console/27871113#comment50529068_27871113)


def git_do(command, into=os.getcwd()):
    """
    Run a git command into specific folder

    Parameters:
        command (array): git parameter to use as array
        into: path from where the command is ran

    """
    command.insert(0, "git")
    subprocess.run(command, cwd=into, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


if __name__ == "__main__":
    readArgs()

    progress(0, TOTAL_STEP, "Getting project list")

    projects = gitlab_get('groups/{}/projects'.format(GROUP_NAME))
    nb_project = len(projects) - 1  # nb of projects minus main project
    project_counter = 1
    TOTAL_STEP = nb_project * TOTAL_STEP

    p = lambda x : ((TOTAL_STEP - 2) * (project_counter - 1)) + x # compute real progression_step
   
    progress(p(1), TOTAL_STEP, "{} projects found".format(nb_project))
    progress(p(2), TOTAL_STEP, "Starting project merging")

    # get the main repo data
    main_repo = [project for project in projects if project['name'] == MAIN_REPO][0]

    for project in projects:
        if project['name'] != main_repo['name']:
            progress(p(3), TOTAL_STEP, "Merging {}/{}".format(project_counter, nb_project))

            # clone project in a temporary file
            git_do(['clone', project['http_url_to_repo']])
            
            progress(p(4) , TOTAL_STEP, "Getting project's branches")

            # get all project's branches
            branches = gitlab_post('projects/{}/repository/branches'.format(project['id']))
            branch_counter = 0

            progress(p(5), TOTAL_STEP, "{} branch found".format(len(branches)))

            # add main repo url as new origin
            git_do(['remote', 'add', MAIN_REPO, main_repo['http_url_to_repo']], project['name'])


            for branch in branches:
                # rename branch if it's project master
                new_branch_name = project['name'] if branch['name'] == 'master' else '{}_{}'.format(project['name'], branch['name'])
                
                progress(p(6 + (0.01*branch_counter)), TOTAL_STEP, "pushing branch {}".format(new_branch_name))

                # checkout branch and push it to new branch in main repo
                git_do(['checkout', branch['name']], project['name'])
                git_do(['push', '-u', MAIN_REPO, '{}:{}'.format(branch['name'], new_branch_name), '--force'], project['name'])


                # protect branch 
                # 0  => No access
                # 30 => Developers + Maintainers + Admin access
                # 40 => Maintainer + Admin access
                # 60 => Admin access
                gitlab_post(
                    'projects/{}/protected_branches'.format(main_repo['id']), 
                    {
                        "name": new_branch_name, 
                        "push_access_level": 30, 
                        "merge_access_level": 30
                    }
                )

                branch_counter += 1

            progress(p(7), TOTAL_STEP, "Deleting temporary files")

            # delete cloned project from local to optimize storage capacity 
            shutil.rmtree(project['name'], ignore_errors=False, onerror=handleRemoveReadonly)

            project_counter += 1

