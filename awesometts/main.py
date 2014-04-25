# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2010-2014  Anki AwesomeTTS Development Team
# Copyright (C) 2010-2012  Arthur Helfstein Fragoso
# Copyright (C) 2013-2014  Dave Shifflett
# Copyright (C) 2012       Dusan Arsenijevic
# Copyright (C) 2013       mistaecko on GitHub
# Copyright (C) 2013       PtrToVoid on GitHub
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from . import (
    VERSION as version,
    STRIP_ALL as service_text,
    STRIP_SOUNDS,
)

import re, time
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QAction,
    QComboBox,
    QDialog,
    QIcon,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from anki.hooks import addHook, wrap
from aqt import mw, utils

from awesometts import config, router
import awesometts.forms as forms


######## utils
def playTTSFromText(text):
    for service, html_tags in getTTSFromHTML(text).items():
        for html_tag in html_tags:
            router.play(
                service,
                ''.join(html_tag.findAll(text=True)),
                html_tag.attrMap,
            )

    for service, bracket_tags in getTTSFromText(text).items():
        for bracket_tag in bracket_tags:
            match = re.match(r'(.*?):(.*)', bracket_tag, re.M|re.I)
            router.play(
                service,
                match.group(2),
                {'voice': match.group(1)},
            )

def getTTSFromText(text):
    tospeak = {}
    for match in re.findall(r"\[(G)TTS:(.*?)\]|\[A?TTS:(.*?):(.*?)\]", text, re.M|re.I):
        service = match[0].lower() if match[0] else match[2].lower()
        value = match[1] if match[0] else match[3]
        if not tospeak.has_key(service):
            tospeak.update({service: [value]})
        else:
            tospeak[service].append(value)
    return tospeak

def getTTSFromHTML(html):
    from BeautifulSoup import BeautifulSoup

    soup = BeautifulSoup(html)
    tospeakhtml = {}

    for htmltag in soup('tts'):
        service = htmltag['service'].lower()
        text = ''.join(htmltag.findAll(text=True)) #get all the text from the tag and stips html
        if text == None or text == '' or text.isspace():
            continue #skip empty tags
        if not tospeakhtml.has_key(service):
            tospeakhtml.update({service: [htmltag]})
        else:
            tospeakhtml[service].append(htmltag)
    return tospeakhtml


############################ Service Forms

def service_form(module, parent):
    lookup = sorted([
        (service_key, service_def, QComboBox())
        for service_key, service_def
        in TTS_service.items()
    ], key=lambda service: service[1]['name'].lower())

    dialog = QDialog(parent)

    form = module.Ui_Dialog()
    form.setupUi(dialog)

    form.comboBoxService.addItems([service[1]['name'] for service in lookup])
    form.comboBoxService.currentIndexChanged.connect(
        form.stackedWidget.setCurrentIndex
    )

    for service_key, service_def, combo_box in lookup:
        combo_box.addItems([voice[1] for voice in service_def['voices']])
        if service_key in config.last_voice:
            try:
                combo_box.setCurrentIndex(service_def['voices'].index(next(
                    voice for voice in service_def['voices']
                    if voice[0] == config.last_voice[service_key]
                )))
            except StopIteration:
                pass

        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(QLabel("Voice:"))
        vertical_layout.addWidget(combo_box)

        stack_widget = QWidget(form.stackedWidget)
        stack_widget.setLayout(vertical_layout)
        form.stackedWidget.addWidget(stack_widget)

        if service_key == config.last_service:
            form.comboBoxService.setCurrentIndex(
                form.stackedWidget.count() - 1
            )

    return lookup, dialog, form

def service_form_values(form, lookup):
    selected = form.comboBoxService.currentIndex()
    service_key, service_def, combo_box = lookup[selected]
    voice = service_def['voices'][combo_box.currentIndex()][0]

    return service_key, service_def, voice

def service_store(anki_callable, path):

    from os import unlink
    from sys import getfilesystemencoding

    return_value = anki_callable(unicode(path, getfilesystemencoding()))

    return return_value


############################ MP3 File Generator

# TODO: It would be nice if a service that sometimes cannot fulfill given
# text (e.g. one using a finite set of prerecorded dictionary words) be made
# to explicitly return False or an exception (instead of None) from its play
# and record callables so that there would be some sort of notification to the
# user that the entered text is not playable.
#
# A convention for this can be established as soon as AwesomeTTS begins
# shipping with at least one bundled service that sometimes returns without
# successfully playing back some text.

def ATTS_Factedit_button(editor):
    lookup, dialog, form = service_form(forms.filegenerator, editor.widget)

    def execute(preview):
        text = form.texttoTTS.toPlainText().strip()
        if not text:
            return

        service_key, service_def, voice = service_form_values(form, lookup)

        if preview:
            service_def['play'](service_text(text), voice)
        else:
            config.update(
                last_service=service_key,
                last_voice=dict(
                    config.last_voice.items() +
                    [(service_key, voice)]
                )
            )

            path = service_def['record'](service_text(text), voice)
            if path:
                service_store(editor.addMedia, path)
            else:
                utils.showWarning("No audio available for text.")

    form.previewbutton.clicked.connect(lambda: execute(preview=True))
    if dialog.exec_():
        execute(preview=False)


#def ATTS_Fact_edit_setupFields(editor):
#    button = QPushButton(editor.widget)
#
#    # FIXME How does one localize Ctrl+T to Cmd+T for the Mac OS X platform?
#    button.setFixedHeight(20)
#    button.setFixedWidth(20)
#    button.setFocusPolicy(Qt.NoFocus)
#    button.setIcon(QIcon(':/icons/speaker.png'))
#    button.setShortcut('Ctrl+t')
#    button.setStyle(editor.plastiqueStyle)
#    button.setToolTip("Insert an audio clip with AwesomeTTS (Ctrl+T)")
#
#    button.clicked.connect(lambda: ATTS_Factedit_button(editor))
#    editor.iconsBox.addWidget(button)
#
#addHook('setupEditorButtons', ATTS_Fact_edit_setupFields)


############################ MP3 Mass Generator


def generate_audio_files(notes, form, service_def, voice, source_field, dest_field):
    update_count = 0
    skip_counts = {
        key: [0, message]
        for key, message
        in [
            ('fields', 'Missing source and/or destination field'),
            ('empty', 'Empty value in the source field'),
            ('unfulfilled', 'Service returned an empty response'),
        ]
    }

    # TODO throttle "batch" threshold and sleep time should be configurable

    nelements = len(notes)
    batch = 900
    throttle = 'throttle' in service_def and service_def['throttle']

    cache_misses = 0
    for c, id in enumerate(notes):
        if throttle and (cache_misses + 1) % batch == 0:
            for t in reversed(range(500)):
                mw.progress.update(label="Generated %s of %s, \n sleeping for %s seconds...." % (c+1, nelements, t))
                time.sleep(1)
        note = mw.col.getNote(id)

        if not (source_field in note.keys() and dest_field in note.keys()):
            skip_counts['fields'][0] += 1
            continue

        mw.progress.update(label="Generating MP3 files...\n%s of %s\n%s" % (c+1, nelements, note[source_field]))

        if note[source_field] == '' or note[source_field].isspace(): #check if the field is blank
            skip_counts['empty'][0] += 1
            continue

        path = service_def['record'](
            service_text(note[source_field]),
            voice,
        )

        # FIXME via router, determine if call required a service call
        # if not path.startswith(CACHE_DIR):
        #     cache_misses += 1

        filename = service_store(mw.col.media.addFile, path)

        if filename:
            if form.radioOverwrite.isChecked():
                if form.checkBoxSndTag.isChecked():
                    note[dest_field] = '[sound:'+ filename +']'
                else:
                    note[dest_field] = filename
            else:
                if form.checkBoxSndTag.isChecked():
                    note[dest_field] = STRIP_SOUNDS(note[dest_field])
                note[dest_field] += ' [sound:'+ filename +']'

            update_count += 1
            note.flush()

        else:
            skip_counts['unfulfilled'][0] += 1

    return nelements, update_count, skip_counts.values()


def onGenerate(browser):
    notes = browser.selectedNotes()
    if not notes:
        utils.showInfo("Select notes before using the MP3 Mass Generator.")
        return

    # TODO it would be nice if this only included fields from selected notes
    import anki.find
    fields = sorted(anki.find.fieldNames(mw.col, downcase=False))

    lookup, dialog, form = service_form(forms.massgenerator, browser)

    form.sourceFieldComboBox.addItems(fields)
    try:
        form.sourceFieldComboBox.setCurrentIndex(
            fields.index(config.last_mass_source)
        )
    except ValueError:
        pass

    form.destinationFieldComboBox.addItems(fields)
    try:
        form.destinationFieldComboBox.setCurrentIndex(
            fields.index(config.last_mass_dest)
        )
    except ValueError:
        pass

    form.label_version.setText("Version %s" % version)

    def dest_handling_changed():
        """Update checkbox label given the new handling behavior."""
        form.checkBoxSndTag.setText(
            dest_handling_changed.OVERWRITE_TEXT
            if form.radioOverwrite.isChecked()
            else dest_handling_changed.ENDOF_TEXT
        )
    dest_handling_changed.ENDOF_TEXT = form.checkBoxSndTag.text()
    dest_handling_changed.OVERWRITE_TEXT = "Wrap Path in [sound:xxx] Tag"

    form.radioEndof.toggled.connect(dest_handling_changed)
    form.radioOverwrite.toggled.connect(dest_handling_changed)

    if not dialog.exec_():
        return

    service_key, service_def, voice = service_form_values(form, lookup)
    source_field = fields[form.sourceFieldComboBox.currentIndex()]
    dest_field = fields[form.destinationFieldComboBox.currentIndex()]

    config.update(
        last_mass_source=source_field,
        last_mass_dest=dest_field,
        last_service=service_key,
        last_voice=dict(
            config.last_voice.items() +
            [(service_key, voice)]
        )
    )

    browser.mw.checkpoint("AwesomeTTS MP3 Mass Generator")
    browser.mw.progress.start(immediate=True, label="Generating MP3 files...")

    browser.model.beginReset()

    process_count, update_count, skip_counts = generate_audio_files(
        notes,
        form,
        service_def,
        voice,
        source_field,
        dest_field,
    )

    browser.model.endReset()
    browser.mw.progress.finish()

    if process_count == update_count:
        utils.showInfo(
            "Note processed and updated." if process_count == 1
            else "%d notes processed and updated." % process_count
        )

    elif process_count == 1:
        utils.showWarning("\n".join(
            ["Could not process note:"] +
            [message for count, message in skip_counts if count],
        ))

    else:
        utils.showWarning("\n".join([
            "Of the %d processed notes..." % process_count,
            "",
        ] + [
            "- %s: %d %s" % (
                message,
                count,
                "note" if count == 1 else "notes",
            )
            for count, message
            in [(update_count, "Successful update")] + skip_counts
            if count
        ]))


#def setupMenu(browser):
#    action = QAction("AwesomeTTS MP3 Mass Generator", browser)
#    action.triggered.connect(lambda: onGenerate(browser))
#
#    browser.form.menuEdit.addAction(action)
#
#addHook("browser.setupMenus", setupMenu)


######################################### Keys and AutoRead

## Check pressed key



# n.b. Previously, before calling playTTSFromText(), these event handlers
# checked to make sure that 'not sound.hasSound(toread)'. I am guessing that
# this was done because AwesomeTTS did not know how to properly deal with
# multiple sounds and they would play simultaneously, but this has been fixed
# now by calling into the Anki playback API.
#
# FIXME. It is possible, I suppose, that people might have the exact same
# audio file on a card via a [sound:xxx] tag as they do as a <tts> template
# tag. We can probably detect this by seeing if two of the same hashed
# filename end up in the queue (and I say "filename" because one would be
# coming from the media directory and another would be coming from the cache
# directory). This would probably need to be fixed in the router by having the
# router examine whether the exact same hashed filename is in the Anki
# playback queue already or looking at the [sound:xxx] tag on the card more
# carefully before playing back the on-the-fly sound.
#
# A similar problem probably exists in reviewer_key_handler for folks who
# includes their question card template within their answer card template and
# whose tts_key_q == tts_key_a.
#
# Unfortunately, it looks like inspecting anki.sound.mplayerQueue won't work
# out on Windows because the path gets blown away by the temporary file
# creation code.
#
# ALTERNATIVELY, if examination of the tag or playback queue turns out to not
# work out so well, this could become two checkbox options on the "On-the-Fly
# Mode" tab for both question and answer sides.

addHook(
    'showQuestion',
    lambda: config.automatic_questions and
        playTTSFromText(mw.reviewer.card.q()),
)

addHook(
    'showAnswer',
    lambda: config.automatic_answers and
        playTTSFromText(mw.reviewer.card.a()),
)


# no other hook, see http://ankisrs.net/docs/addons.html; pylint:disable=W0212

def reviewer_key_handler(evt, _old):
    """
    Examines the key event to see if the user has triggered one of their
    shortcut options.

    If we do not handle the key here, then it is passed through to the
    normal Anki Reviewer implementation.
    """

    if mw.reviewer.state not in ['answer', 'question']:
        return

    code = evt.key()
    passthru = True

    if code in [Qt.Key_R, Qt.Key_F5]:
        # if the user sets his/her shortcut the one of the built-in audio
        # shortcuts, we will play all sounds, starting with the built-in(s)

        _old(evt)
        passthru = False

    if code == config.tts_key_q:
        playTTSFromText(mw.reviewer.card.q())
        passthru = False

    if mw.reviewer.state == 'answer' and code == config.tts_key_a:
        playTTSFromText(mw.reviewer.card.a())
        passthru = False

    if passthru:
        _old(evt)

mw.reviewer._keyHandler = wrap(
    mw.reviewer._keyHandler,
    reviewer_key_handler,
    'around',  # setting 'around' allows me to block call to original function
)
