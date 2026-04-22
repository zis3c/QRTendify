from django import forms

from ..models import CertificateTemplate


class CertificateTemplateForm(forms.ModelForm):
    """Upload and configure certificate templates."""

    class Meta:
        model = CertificateTemplate
        fields = [
            "template_file",
            "is_active",
            "name_x_position",
            "name_y_position",
            "font_name",
            "font_size",
            "font_color",
        ]
        widgets = {
            "template_file": forms.FileInput(
                attrs={
                    "accept": ".pdf",
                    "class": "w-full p-2 border border-gray-300 rounded-lg",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 text-blue-600 rounded focus:ring-blue-500"}
            ),
            "name_x_position": forms.NumberInput(
                attrs={
                    "class": "w-full p-2 border border-gray-300 rounded-lg",
                    "min": "0",
                }
            ),
            "name_y_position": forms.NumberInput(
                attrs={
                    "class": "w-full p-2 border border-gray-300 rounded-lg",
                    "min": "0",
                }
            ),
            "font_name": forms.Select(
                attrs={"class": "w-full p-2 border border-gray-300 rounded-lg"}
            ),
            "font_size": forms.NumberInput(
                attrs={
                    "class": "w-full p-2 border border-gray-300 rounded-lg",
                    "min": "8",
                    "max": "72",
                }
            ),
            "font_color": forms.TextInput(
                attrs={
                    "class": "w-full p-2 border border-gray-300 rounded-lg",
                    "type": "color",
                }
            ),
        }
        help_texts = {
            "template_file": "Upload a PDF template. The attendee name will be overlaid on this.",
            "name_x_position": "Distance from left edge in pixels (try 300 for center)",
            "name_y_position": "Distance from bottom edge in pixels (try 400 for middle)",
            "font_size": "Font size in points (24-36 recommended)",
        }
