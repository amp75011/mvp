Step 2: Initialize the Translations Directory
Run the following command in your terminal to create the necessary directories and files for translations:

bash
Copy code
pybabel extract -F babel.cfg -o translations/messages.pot .
This command generates a messages.pot file in a new translations directory. This file is a template used to create language-specific .po files.

Step 3: Create Language-Specific .po Files
For each language you want to support, initialize a .po file. For example, to add French support:

bash
Copy code
pybabel init -i translations/messages.pot -d translations -l fr
This command creates a French translation file at translations/fr/LC_MESSAGES/messages.po.

!!!!!!!! use this one instead:
Update .po File:

Update the .po file with new messages:
css
Copy code
pybabel update -i messages.pot -d translations
translations is the directory where your .po files are stored.
!!!!!!!!

Step 4: Translate and Compile the Translations
Open translations/fr/LC_MESSAGES/messages.po in a text editor.

Add translations for each string in the msgstr fields.

Compile the translations:

bash
Copy code
pybabel compile -d translations
Additional Tips: 
The .po file needs manual translation. You have to enter the appropriate translated text for each msgid.
If you add more translatable strings to your application later, rerun the extract command, update the .po files with new translations, and recompile.


Spend Wisely, Live Sustainably
Find the Best Prices, and Discover Greener, Healthier Choices!

Dépensez moins, vivez mieux                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
Trouvez les meilleurs prix, et découvrez des alternatives responsables !


****************
babel.cfg:
[python: **.py]
[jinja2: templates/**.html]
extensions=jinja2.ext.autoescape,jinja2.ext.with_

extraction:
pybabel extract -F babel.cfg -o messages.pot .

initialisation (new language):
pybabel init -i messages.pot -d translations -l [lang_code]

update (existing language):
pybabel update -i messages.pot -d translations

TRANSLATION

compilaton:
pybabel compile -d translations

