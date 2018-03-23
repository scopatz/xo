$PROJECT = 'xo'
$ACTIVITIES = ['version_bump', 'changelog', 'tag', 'push_tag', 'pypi',
               'conda_forge', 'ghrelease']

$VERSION_BUMP_PATTERNS = [
    ('setup.py', "VERSION\s*=.*", "VERSION = '$VERSION'"),
    ('xo.py', "__version__\s*=.*", "__version__ = '$VERSION'"),
    ]

$TAG_REMOTE = 'git@github.com:scopatz/xo.git'

$GITHUB_ORG = 'scopatz'
$GITHUB_REPO = 'xo'
