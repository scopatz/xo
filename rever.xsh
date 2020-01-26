$PROJECT = 'xo'
$ACTIVITIES = ['version_bump', 'changelog', 'tag', 'push_tag', 'pypi',
               'ghrelease', 'conda_forge']

$VERSION_BUMP_PATTERNS = [
    ('setup.py', r"VERSION\s*=.*", "VERSION = '$VERSION'"),
    ('xo.py', r"__version__\s*=.*", "__version__ = '$VERSION'"),
    ]

$TAG_REMOTE = 'git@github.com:scopatz/xo.git'

$GITHUB_ORG = 'scopatz'
$GITHUB_REPO = 'xo'
