# Merge Gitlab group's projects into one 
Migrate all branches of all projects of gitlab group into a main project

## Migration utility for moving multiple Gitlab project into a main repo as branches
This tool provide an automated way to push all repository in a Gitlab group into a main repository as branch. All branches are copied. Perfect way to modernize your versioning organization

## Usage
Type `python migrate_to_one_project.py --help` for usage information.
```
usage: 
  migrate_to_one_project.py [-h] api-token group-name main-repo branch-protection-level

required arguments:
  api-token                 Token mandatory to use gitlab API see gitlab documentation 
                            at https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html
  group-name                Name of the group where all projects are.
  main-repo                 The repository where all the other group's projects will be pushed as 
                            branches
  branch-protection-level   Right of push and merge on your branches. 
                              0  => No protection
                              30 => Developers + Maintainers + Admin
                              40 => Maintainer + Admin 
                              60 => Admin only

optional arguments:
  -h, --help              show this help message and exit
```

## Requirements
This tool was written using Python 3 librairies
