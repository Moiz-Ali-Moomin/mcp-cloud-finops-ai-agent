CURRENT_PROJECT = None

def set_project(project_id: str):
    global CURRENT_PROJECT
    CURRENT_PROJECT = project_id

def get_project():
    return CURRENT_PROJECT
