
from paco.models.references import get_model_obj_from_ref
import os
import pathlib
from chameleon import PageTemplateLoader
import chameleon.loader
from paco.models.locations import get_parent_by_interface
from paco.models import schemas
from paco.utils import prefixed_name


# Generic Resource templates
# if 'res-<resource.type>.pt' does not exist, the template will return the generic 'res-empty.pt'.
# Chameleon needs a big ugly monkey patch on the TemplateLoader.load() method to achieve this ...
def generic_resource_load(self, spec, cls=None):
    if cls is None:
        raise ValueError("Unbound template loader.")

    spec = spec.strip()

    if self.default_extension is not None and '.' not in spec:
        spec += self.default_extension

    if ':' in spec:
        spec = chameleon.loader.abspath_from_asset_spec(spec)

    if not os.path.isabs(spec):
        for path in self.search_path:
            path = os.path.join(path, spec)
            if os.path.exists(path):
                spec = path
                break
        else:
            if spec.startswith('res-'):
                spec = os.path.join(self.search_path[0], 'res-empty.pt')
            else:
                raise ValueError("Template not found: %s." % spec)

    return cls(spec, search_path=self.search_path, **self.kwargs)
chameleon.loader.TemplateLoader.load = generic_resource_load


def has_alarms(res):
    if getattr(res, 'monitoring', None) != None:
        if getattr(res.monitoring, 'alarm_sets', None) != None:
            if len(res.monitoring.alarm_sets) > 0:
                return True
    return False

def has_logs(res):
    if getattr(res, 'monitoring', None) != None:
        if getattr(res.monitoring, 'log_sets', None) != None:
            if len(res.monitoring.log_sets) > 0:
                return True
    return False

def parent_obj(child_obj, interfacename):
    return get_parent_by_interface(child_obj, getattr(schemas, interfacename))

def display_project_as_html(project, output):
    path = os.path.dirname(__file__)
    static_path = pathlib.Path(path) / 'static'
    templates = PageTemplateLoader(path)
    templates.registry
    userinfo = project.credentials

    def resolve_ref(ref_string):
        return get_model_obj_from_ref(ref_string, project)

    html_files = {}
    for tmpl in ['index.pt', 'accounts.pt', 'globalresources.pt', 'netenvs.pt', 'monitoring.pt']:
        fname = tmpl[:-2] + 'html'
        html_files[fname] = templates[tmpl](
            project=project,
            userinfo=userinfo,
            resolve_ref=resolve_ref,
            templates=templates,
            output=output,
        )

    # Environments
    envs_html = {}
    env_tmpl = templates['env.pt']
    for netenv in project['netenv'].values():
        for env in netenv.values():
            envs_html[f'ne-{netenv.name}-{env.name}.html'] = env_tmpl(
                project=project,
                netenv=netenv,
                env=env,
                userinfo=userinfo,
                templates=templates,
                has_alarms=has_alarms,
                has_logs=has_logs,
                resolve_ref=resolve_ref,
                parent_obj=parent_obj,
                prefixed_name=prefixed_name,
                output=output,
            )

    return static_path, html_files, envs_html
