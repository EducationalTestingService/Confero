"""
Creates the end user Confero distribution.

1) Use a base folder / file structure and copy it.
   This would include things like the binary dependencies and
   other files that do not change.

2) Add the latest ConferoView folder

3) Add the latest ConferoTrack folder

4) Copy latest psychopy / iohub to site-packages

[MANUALLY] 5) Build user docs

6) add built html docs to
    a. Top level Confero folder
    b. Confero/ConferoView/view/static folder

7) Copy latest .bat files to top level Confero folder.

[NOT YET DONE] 8) Modify some file that can be used to hold a build date / version number
   for the distribution.

[MANUALLY] 9) Create the self extracting archive file from the newly built Confero distro
"""
import os, sys, subprocess
import distutils.core
import dateutil
import shutil

CONFERO_SOURCE_ROOT = "../"
BASE_DISTRO_TEMPLATE_CONTENTS = "../../Confero_Distro_Template"
NEW_DISTRIBUTION_ROOT_DIR = "D:/Confero"
PSYCHOPY_SOURCE_ROOT = "../../psychopy"
REMOVE_PSYCHOPY_BUILD_FOLDERS = ['build', 'PsychoPy.egg-info', 'dist']
CONFERO_DOCS_ROOT = "../docs"

def nabs(file_path):
    return os.path.normcase(os.path.normpath(os.path.abspath(file_path)))

CONFERO_SOURCE_ROOT = nabs(CONFERO_SOURCE_ROOT)
CONFERO_DOCS_ROOT = nabs(CONFERO_DOCS_ROOT)
BASE_DISTRO_TEMPLATE_CONTENTS = nabs(BASE_DISTRO_TEMPLATE_CONTENTS)
BASE_DISTRO_TEMPLATE_CONTENTS = nabs(BASE_DISTRO_TEMPLATE_CONTENTS)
NEW_DISTRIBUTION_ROOT_DIR = nabs(NEW_DISTRIBUTION_ROOT_DIR)
PSYCHOPY_SOURCE_ROOT = nabs(PSYCHOPY_SOURCE_ROOT)

print "=== Confero End User Distribution Build Started ==="
print

# Remove Distro if already exists
try:
    shutil.rmtree(NEW_DISTRIBUTION_ROOT_DIR)
    print "Removed:", NEW_DISTRIBUTION_ROOT_DIR
    print
except Exception, e:
    print ">> Not Removed: ", NEW_DISTRIBUTION_ROOT_DIR
    print "   Reason:", e

# copy initial distro contents template
print ">> Copying Base Distribution Template ....\n   This can take a long time ...."
distutils.dir_util.copy_tree(BASE_DISTRO_TEMPLATE_CONTENTS, NEW_DISTRIBUTION_ROOT_DIR)
print
print ">> Copied: ", BASE_DISTRO_TEMPLATE_CONTENTS, "to" , NEW_DISTRIBUTION_ROOT_DIR
print
## Build latest PsychoPy

print ">> Starting PsychoPy build..."
# Remove any existing build / dist / PsychoPy.egg-info
for subdir in REMOVE_PSYCHOPY_BUILD_FOLDERS:
    deldir = os.path.join(PSYCHOPY_SOURCE_ROOT, subdir)
    try:
        shutil.rmtree(deldir)
        print "   - Removed:",deldir
    except Exception, e:
        print "   * Not Removed:", deldir
        print "      Reason:", e

print ">> running python setup.py install..."
os.chdir(PSYCHOPY_SOURCE_ROOT)
subprocess.check_output("python setup.py install", stderr=subprocess.STDOUT, shell=True)
print
print "Copying PsychoPy build ..."

psycho_source_to_copy = nabs(os.path.join(PSYCHOPY_SOURCE_ROOT, 'build/lib/psychopy'))
copy_to_site_packages = nabs(os.path.join(NEW_DISTRIBUTION_ROOT_DIR, 'python-2.7.6/Lib/site-packages/psychopy'))

distutils.dir_util.copy_tree(psycho_source_to_copy, copy_to_site_packages)
print
print ">> Copied: ", psycho_source_to_copy, "to" , copy_to_site_packages
print

# Copy ConferoTrack Folders
print "** Copying Confero Track Source ...."
CONFERO_TRACK_SOURCE_ROOT = os.path.join(CONFERO_SOURCE_ROOT,'ConferoTrack')
CONFERO_DISTRO_TRACK_ROOT = os.path.join(NEW_DISTRIBUTION_ROOT_DIR,'ConferoTrack')
print "   Copying:",os.path.join(CONFERO_TRACK_SOURCE_ROOT,'lib')
distutils.dir_util.copy_tree(os.path.join(CONFERO_TRACK_SOURCE_ROOT,'lib'),
                             os.path.join(CONFERO_DISTRO_TRACK_ROOT,'lib'))
print "   Copying:",os.path.join(CONFERO_TRACK_SOURCE_ROOT,'settings')
distutils.dir_util.copy_tree(os.path.join(CONFERO_TRACK_SOURCE_ROOT,'settings'),
                             os.path.join(CONFERO_DISTRO_TRACK_ROOT,'settings'))
print "   Copying:",os.path.join(CONFERO_TRACK_SOURCE_ROOT,'track')
distutils.dir_util.copy_tree(os.path.join(CONFERO_TRACK_SOURCE_ROOT,'track'),
                             os.path.join(CONFERO_DISTRO_TRACK_ROOT,'track'))
default_results_dir = os.path.join(CONFERO_DISTRO_TRACK_ROOT,"results","default_experiment")
print "   Making default results dir:", default_results_dir
if not os.path.exists(default_results_dir):
    os.makedirs(default_results_dir)
print

# Copy ConferoView Folders
print "** Copying Confero View Source ...."
CONFERO_VIEW_SOURCE_ROOT = os.path.join(CONFERO_SOURCE_ROOT,'ConferoView')
CONFERO_DISTRO_VIEW_ROOT = os.path.join(NEW_DISTRIBUTION_ROOT_DIR,'ConferoView')
print "   Copying:",os.path.join(CONFERO_VIEW_SOURCE_ROOT,'settings')
distutils.dir_util.copy_tree(os.path.join(CONFERO_VIEW_SOURCE_ROOT,'settings'),
                             os.path.join(CONFERO_DISTRO_VIEW_ROOT,'settings'))
print "   Copying:",os.path.join(CONFERO_VIEW_SOURCE_ROOT,'view')
distutils.dir_util.copy_tree(os.path.join(CONFERO_VIEW_SOURCE_ROOT,'view'),
                             os.path.join(CONFERO_DISTRO_VIEW_ROOT,'view'))

print
print "** Doc build is not working, copy existing doc build.. **"
#print
#print "** Building Confero HTML Documentation ...."
#print "CONFERO_DOCS_ROOT:", CONFERO_DOCS_ROOT
## Build latest User manual
#remove the build dir
#try:
#    shutil.rmtree(docs_build_dir)
#    print "   - Removed:",docs_build_dir
#except Exception, e:
#    print "   * Not Removed:", docs_build_dir
#    print "      Reason:", e

#print
#print "Running make html"
#subprocess.check_output("%s html"%(os.path.join(CONFERO_DOCS_ROOT,'make.bat')), stderr=subprocess.STDOUT, shell=True)

os.chdir(CONFERO_DOCS_ROOT)
docs_build_dir = nabs(os.path.join(CONFERO_DOCS_ROOT,'build'))
print "    docs_build_dir:",docs_build_dir

DOCS_HTML_BUILD_ROOT = nabs(os.path.join(docs_build_dir,'html'))
NEW_DISTRIBUTION_DOCS_DIR = nabs(os.path.join(NEW_DISTRIBUTION_ROOT_DIR,'docs'))
NEW_DISTRIBUTION_SERVER_DOCS_DIR = nabs(os.path.join(NEW_DISTRIBUTION_ROOT_DIR,'ConferoView/View/static/docs'))

print
print "* Copy docs build to distro..."
print "    Copying %s to %s"%(DOCS_HTML_BUILD_ROOT,NEW_DISTRIBUTION_DOCS_DIR)
distutils.dir_util.copy_tree(DOCS_HTML_BUILD_ROOT, NEW_DISTRIBUTION_DOCS_DIR)
print "    Copying %s to %s"%(DOCS_HTML_BUILD_ROOT,NEW_DISTRIBUTION_SERVER_DOCS_DIR)
distutils.dir_util.copy_tree(DOCS_HTML_BUILD_ROOT, NEW_DISTRIBUTION_SERVER_DOCS_DIR)