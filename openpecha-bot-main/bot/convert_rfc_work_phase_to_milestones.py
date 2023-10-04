from typing import List, Tuple


class Issue:
    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body


class Milestone:
    def __init__(self, title: str, issues: List[Issue]):
        self.title = title
        self.issues = issues

    def create(self):
        # TODO: create github milestone
        # TODO: create github issues with milestone assigned
        ...


def strip_title(text: str) -> str:
    return "\n".join(text.splitlines()[1:])


def get_implementation_and_documentation(rfc: str) -> Tuple[str, str]:
    implementation_identifier = '<h3 id="implementation">Implementation</h3>'
    documentation_indentifier = '<h3 id="documentation">Documentation</h3>'

    implementation_start_idx = rfc.find(implementation_identifier)
    documentation_start_idx = rfc.find(documentation_indentifier)

    implementation = rfc[implementation_start_idx:documentation_start_idx]
    documentation = rfc[documentation_start_idx:]

    return strip_title(implementation), strip_title(documentation)


def get_implementation_milestones(
    implementation: str,
) -> List[Milestone]:
    milestone_marker = "**"
    milestones: List[Milestone] = []
    current_milestone_issues: List[Issue] = []
    current_milestone_title = ""
    current_issue_body = ""
    for line in implementation.strip().splitlines():

        # check for milestone title which is in bold (**<title>**)
        if line.startswith(milestone_marker):
            current_milestone_title = line.strip(milestone_marker)

        # check for task, which is an issue
        elif line.startswith("-"):
            # add prvious issue's body
            if current_issue_body:
                current_milestone_issues[-1].body = current_issue_body
                current_issue_body = ""

            issue = Issue(title=current_milestone_title, body=current_issue_body)
            current_milestone_issues.append(issue)

        # check for sub tasks, which are body of the current issue
        elif line.startswith("  ") or line.startswith("\t"):
            current_issue_body += line + "\n"

        # reach end of milestone, which is one empty line
        else:
            if current_issue_body:
                current_milestone_issues[-1].body = current_issue_body
            milestone = Milestone(
                title=current_milestone_title, issues=current_milestone_issues
            )
            milestones.append(milestone)
            current_milestone_issues = []
            current_milestone_title = ""
            current_issue_body = ""

    if current_milestone_issues:
        milestone = Milestone(
            title=current_milestone_title, issues=current_milestone_issues
        )
        milestones.append(milestone)

    return milestones


def get_milestones_from_work_phase(rfc: str) -> List[Milestone]:
    implementation, documentation = get_implementation_and_documentation(rfc)

    implementation_milestones = get_implementation_milestones(implementation)

    return implementation_milestones
