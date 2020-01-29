import os
import csv
import git
from issues import get_jira_issues
from datetime import datetime
from versions import get_repo_versions
from caching import REPOSIROTY_DATA_DIR
from fixing_issues import get_commits_between_versions, Version_Info, commits_and_issues,clean_commit_message
from commit import Commit
from caching import cached
from apache_repos import get_apache_repos_data

VERSIONS = os.path.join(REPOSIROTY_DATA_DIR, r"apache_versions")

def get_repo_adata(repo_path, jira_key):

    if not os.path.exists(repo_path):
        print "start git clone https://github.com/apache/{0}.git".format(os.path.basename(repo_path))
        return

    versions = get_repo_versions(repo_path)
    if len(versions) < 4:
        print ("Less than 5 versions for repo, aborting")
        return

    save_tickets_stats(os.path.join(VERSIONS, jira_key) + "_STATS.csv", repo_path, r"http://issues.apache.org/jira", jira_key, versions)

#Get connection between commit and issue and add issue info to commit
def commits_and_all_issues(repo, issues):
    def replace(chars_to_replace, replacement, s):
        temp_s = s
        for c in chars_to_replace:
            temp_s = temp_s.replace(c, replacement)
        return temp_s

    def get_bug_num_from_comit_text(commit_text):
        text = replace("[]?#,:()", "", commit_text.lower())
        text = replace("-_", " ", text)
        for word in text.split():
            if word.isdigit():
                return word
        return "0"
    commits = []
    #issues_ids = map(lambda issue: issue.key.split("-")[1], issues)
    for git_commit in repo.iter_commits():
        commit_text = clean_commit_message(git_commit.summary)
        commit_issue_num = get_bug_num_from_comit_text(commit_text)
        if commit_issue_num in issues.keys():
            commits.append(Commit.init_commit_by_git_and_issue(git_commit, issues[commit_issue_num]))
    return commits


@cached(r"apache_commits_data")
def get_jira_data(jira_project_name, jira_url, gitPath):
    repo = git.Repo(gitPath)
    dict_issues = {x.key.strip().split("-")[1]:x for x in get_jira_issues(jira_project_name, jira_url)}
    #issues = map(lambda x: x.key.strip(), get_jira_issues(jira_project_name, jira_url))
    commits = commits_and_all_issues(repo, dict_issues)
    print jira_project_name, "num issues: " , len(dict_issues.keys()), "num bug commits: ", len(filter(lambda c: c.is_bug(), commits))
    return commits



class Ticket_Version_Info(object):
    def __init__(self, tag, commits, types):
        self.tag = tag
        self.tag_files = tag._commit._files
        self.num_commits = len(commits)
        self.type_commits = {}
        self.type_files = {}
        for t in types:
            self.type_commits[t] = filter(lambda commit: commit._issue.type == t, commits)
            self.type_files[t] = self.get_commits_files(self.type_commits[t])
        bugged_commits = filter(lambda commit: commit._bug_id != "0", commits)
        self.num_bugged_commits = len(bugged_commits)
        self.commited_files = self.get_commits_files(commits)
        self.bugged_files = self.get_commits_files(bugged_commits)
        # self.commits_diff = self.get_commit_diffs(commits)

    @staticmethod
    def get_commits_files(commits):
        return set(reduce(list.__add__, map(lambda commit: commit._files, commits), []))

#get types of issues in JIRA
def get_jira_types(commits):
    #MICHAL - number of non-bug commits, check the issues
    issue_types = set([x._issue.type for x in commits])
    type_commits = {}
    for t in issue_types:
        type_commits[t] = sum(c._issue.type == t for c in commits)
    for k, v in type_commits.items(): print k, ": ", v
    return type_commits.keys()



def get_jira_files_between_versions(gitPath, jira_url, jira_project_name, versions):
    commits = get_jira_data(jira_project_name, jira_url, gitPath)
    commit_types = get_jira_types(commits)
    tags_commits = get_commits_between_versions(commits, versions)

    sorted_tags_commits = sorted(tags_commits.items(), key=lambda x: x[0]._commit._commit_date)
    save_tickets_all(gitPath, jira_url, jira_project_name,
        os.path.join(VERSIONS, jira_project_name) + "_ALL.csv", sorted_tags_commits )

    tags = []
    for tag in tags_commits:
        tags.append(Ticket_Version_Info(tag, tags_commits[tag], commit_types))
        return commit_types, sorted(tags, key=lambda x: x.tag._commit._commit_date)


def save_tickets_all(gitPath, jira_url, jira_project_name, out_file, tags_commits):

    git_project_name = os.path.basename(gitPath)
    with open(out_file, "wb") as f:
        writer = csv.writer(f)

        #Link for github example: https://github.com/apache/distributedlog/commit/083eddb9d5a255e0303255f12cd2d681e49d2f53
        #link for jira example: https://issues.apache.org/jira/projects/DL/issues/DL-206  (DL=JIRA KEY)
        writer.writerow(["type ticket", "t status", "t resolution", "ticket_id", "date",
                         "num files", "num commits", "ticket summary", "commit msg","commit_id",
                         "num additions", "num deletions", "num lines"
                         "git link", "jira link"])
        for tag, list_commits in tags_commits:

            writer.writerow(["tag", "", "", tag._name,  datetime.fromtimestamp(tag._commit._commit_date).strftime("%Y-%m-%d"),
                             len(tag.version_files), len(list_commits), "", "", "", "",
                             "", "", "", "", ""])
            for c in list_commits:
                try:
                    git_link = os.path.join("https://github.com/apache", git_project_name, "commit", c._commit_id)
                    jira_link = os.path.join("https://issues.apache.org/jira/projects", jira_project_name, "issues", c._issue.key)
                    writer.writerow([c._issue.type, c._issue.status, c._issue.resolution, c._bug_id, datetime.fromtimestamp(c._commit_date).strftime("%Y-%m-%d"),
                                 len(c._files), "1",  c._issue.summary, c._commit_message, c._commit_id,
                                     c._num_additions, c._num_deletions, c._num_lines,
                                     git_link, jira_link])
                except:
                    print("failed to write row for bug_id " + c._bug_id)




def save_tickets_stats(out_file, gitPath, jira_url, jira_project_name, versions):
    types, tags = get_jira_files_between_versions(gitPath, jira_url, jira_project_name, versions)
    with open(out_file, "wb") as f:
        writer = csv.writer(f)
        titles = ["version_name", "#commited files in version", "#bugged files in version", "bugged_ratio",
                         "#commits", "#bugged_commits", "#ratio_bugged_commits", "version_date"]
        for t in types:
            titles.append(t + " files")
            titles.append(t + " commits")

        writer.writerow(titles)
        for tag in tags:
            commited_java_files = filter(lambda x: "java" in x, tag.commited_files)
            num_commited_java_files = len(commited_java_files)
            bugged_flies = len(filter(lambda x: "java" in x,  tag.bugged_files))
            bugged_ratio = 0
            if num_commited_java_files != 0:
                bugged_ratio = 1.0 * bugged_flies / num_commited_java_files
            ratio_bugged_commits = 0
            if tag.num_commits:
                ratio_bugged_commits = 1.0 * tag.num_bugged_commits / tag.num_commits
            type_data = []
            for t in types:
                type_data += [len(tag.type_files[t]) , len(tag.type_commits[t])]
            writer.writerow([tag.tag._name, num_commited_java_files, bugged_flies, bugged_ratio, tag.num_commits,
                             tag.num_bugged_commits, ratio_bugged_commits,
                             datetime.fromtimestamp(tag.tag._commit._commit_date).strftime("%Y-%m-%d")] + type_data)





if __name__ == "__main__":

    get_repo_adata('C:\\temp\\apache_repos\\logging-log4j2', 'log4j2')

    pass



