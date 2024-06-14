The principle is to change only what needs to be changed so that code base can be understood by all developers

Identify a true problem with the code or a feature that needs to be implemented. Typically the project owner creates these.   New developers to the project can make suggestions but should get approval for them.  These are 'problems' or issues that are specific and focused.   

Create a gitlab issue in the project describing the problem or feature.  The problem or feature should be clearly defined first, then if there are possible solutions to that, those can be described after that. 

Before suggesting new issues, developers can pick an issue of the existing issues in gitlab.  For us that list is https://gitlab.msu.edu/Enviroweather/ewxpwsdb/-/issues  Sometimes to fix an issue raises a new issue and that should be created as described above and in the text I sent. 

Discuss with project manager which issues are priority and ready to take on, either because the project manager has assigned you the issue,   or as you work more on the project, you  self-assigned

Create a branch for tackling this issue.  Name the branch with the issue name, and a short abbrevion of the issue.   For example, if the issue is "#4 off by one error"  the branch could be named "4-off-by-one"

this allow team members to identify which issue the branch addresses.  If the branch has to address multiple , closely-related issues, name it with both number, for example "20-21-connection-issues" or something.   However mostly just create a new branch for each issue, no matter how small.  this minimized merge conflicts.   Check out the branch from the main line (which is sometimes "main" and sometimes "dev" if main is used for the "golden branch" or "production branch"

change the code only to address the issue.  I had to learn this the hard way working on software deve teams.  It's tempting to delete comments, clean up white space, etc but don't.   This way the commit shows only the exact changes needed to address the issue

When you add commits to that branch, include the issue number in the commit.  This also allows one to refer back to the issue when reviewing a commit.  Using the previous example with issue "#4 off by one error"  a commit message may be "set counter correctly #4"    If the commit completely fixes the issue, then you can also use the commit message "set counter correctly, closes #4" 

Note the commit message doesn't reference the file updated, as that is already evident in the diff for the commit, the list of files changed.   

this example may seem tiny, but tiny changes can sometime affect other code and team members need to know about it. 

commit and push the changes to the branch.  For most instances, then create a "merge request" and ask for another dev on the team to reaview it.  If it's just you and the project manager then ask the project manager to review.  When creating a merge request, create a name with the issue in it, e.g. "Closes #4"

If you are asked to review a merge request, then save your current branch, check out main (or dev as the case may be), then then checkout the person's issue branch and if necessary pull the latest changes for that branch.  Make changes to configuration file (.env, config.txt, app.json, etc) if necessary and try to run the tests and use the program.   If it looks good, comment on the merge reequest that it's ready to be merge into main

if there are problems with tests, etc, then indicate in a comment to the merge request, or if it's a related to the nature of the issue (for example, you may find it was not actually an off-by-one error but something else) comment on the issue.   either way, it's best to communicate.  


If you get a comment back about your changes asking to do them differently or asking to make more changes, then do so in your branch, push again and add a comment to the merge request that you are ready for a new review.   

If you use gitlab to complete the merge of an issue branch into main, then also delete the branch in gitlab.   Close the issue if it is not closed automatically.     When closing add a comment for the 

-- 
This may seem like more work than just fixing all the bugs and cleaning up all the comments, but essential for good team working.   Working together on a code base is like sharing a workbench.  If you re-organize all the drawers and clean things up, then your teammates may not be able to find anything, even if it looks much better.   sometimes everyone agrees that needs to be done and it's ok but make sure it is first.   



