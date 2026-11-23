from django.forms.renderers import TemplatesSetting


class SiteFormRenderer(TemplatesSetting):
    """
    Renders every Django form with templates/forms/form.html and
    templates/forms/field.html, so {{ form }} produces the same accessible
    markup (label, input, help text, errors) across the whole site.
    """

    form_template_name = "forms/form.html"
    field_template_name = "forms/field.html"
