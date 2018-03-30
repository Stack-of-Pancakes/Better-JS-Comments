# Complete waste of time

Extended functionality of Sublime Text commenting to use a stupid custom set of comment characters for files using Javascript or JSON syntax.  The built-in way of handling this can't be changed to add unique comment strings on each line as the existing implementation just uses either a single string for commenting single lines, or two different strings for commenting blocks of code.  There is no way to make the strings used for commenting dynamic by just editing the .sublime-syntax files for Javascript/JSON.

Then I had to add a readme because gists limit the size of a file's description.  At which point I'm like screw it, I'll just upload it to GitHub instead.  I still don't understand why I'm wasting so much of my life on this.

### Installing

1. From the "Preferences" menu choose "Browse Packages..."
2. In that folder create a new folder named "Default"
3. In the "Default" folder save this file as "comment.py"