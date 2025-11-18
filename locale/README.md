# Locale Files - MEC Previsioni

This directory contains internationalization (i18n) translation files for the MEC Previsioni application.

## Structure

```
locale/
├── README.md           # This file
├── it/                 # Italian translations
│   └── rotture.json   # Breakdowns module translations (IT)
└── en/                 # English translations
    └── rotture.json   # Breakdowns module translations (EN)
```

## File Format

Each locale file is a JSON file with the following structure:

```json
{
  "module": "module_name",
  "language": "language_code",
  "translations": {
    "key": "translated_text",
    "nested": {
      "key": "translated_text"
    }
  }
}
```

## Modules

### Rotture (Breakdowns)

The `rotture.json` files contain all translations for the breakdowns file processing module, including:

- **UI Elements**: Page titles, buttons, labels
- **Messages**: Success/error messages, notifications
- **Forms**: Form field labels, placeholders, help text
- **Tables**: Column headers, status badges
- **Modals**: Dialog titles, confirmation messages
- **Processing**: File processing status messages and traces

## Language Codes

- `it` - Italian (Italiano)
- `en` - English

## Usage

These locale files are meant to externalize all hardcoded strings from the application, making it easier to:

1. **Maintain translations**: All text is in one place per module
2. **Support multiple languages**: Easy to add new language files
3. **Update UI text**: No need to search through templates and code
4. **Ensure consistency**: Reuse common translations across the app

## Future Implementation

To use these locale files in the application, you would need to:

1. Install Flask-Babel or a similar i18n library
2. Create a locale loader that reads these JSON files
3. Update templates to use translation functions (e.g., `{{ _('key') }}`)
4. Update Python code to use translation functions for flash messages

Example with Flask-Babel:

```python
from flask_babel import Babel, gettext

# In templates
{{ _('rotture.title') }}

# In Python code
flash(gettext('rotture.messages.file_uploaded').format(filename=filename))
```

## Adding New Translations

When adding new features:

1. Create entries in both `it/module.json` and `en/module.json`
2. Use descriptive keys organized by section
3. Use `{variable}` syntax for dynamic content
4. Keep HTML tags in translations when needed for formatting

Example:
```json
{
  "messages": {
    "file_uploaded": "File {filename} caricato con successo!"
  }
}
```

## Translation Key Naming Convention

- Use lowercase with underscores: `file_uploaded`
- Group by functionality: `form.year`, `messages.error`, `buttons.save`
- Be descriptive: prefer `file_info_uploaded` over `uploaded`
- Use plural forms when needed: `rotture_deleted` vs `rottura_deleted`

## Notes

- All Italian translations are complete for the rotture module
- English translations are provided as examples and for future internationalization
- HTML tags and formatting are preserved in translations where needed
- Variable placeholders use `{variable_name}` format

## Version History

- **v1.0** (2025-11-18): Initial locale files created for rotture (breakdowns) module
  - Added complete Italian (it) translations
  - Added complete English (en) translations
  - Covers all templates: list, create, edit
  - Covers all routes: messages, errors, processing traces
