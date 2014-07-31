# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2014       Anki AwesomeTTS Development Team
# Copyright (C) 2014       Dave Shifflett
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

"""
Sound tag-stripper dialog
"""

__all__ = ['BrowserStripper']

from PyQt4 import QtCore, QtGui

from .base import Dialog


class BrowserStripper(Dialog):
    """
    Provides a dialog that can be invoked when the user wants to remove
    [sound] tags from a selection of notes in the card browser.
    """

    __slots__ = [
        '_alerts',   # callable for reporting errors and summaries
        '_browser',  # reference to the current Anki browser window
        '_notes',    # list of Note objects selected when window opened
    ]

    def __init__(self, browser, alerts, *args, **kwargs):
        """
        Sets our title and initializes our selected notes.
        """

        self._alerts = alerts
        self._browser = browser
        self._notes = None  # set in show()

        super(BrowserStripper, self).__init__(
            title="Remove Audio from Selected Notes",
            *args, **kwargs
        )

    # UI Construction ########################################################

    def _ui(self):
        """
        Prepares the basic layout structure, including the intro label,
        scroll area, radio buttons, and help/okay/cancel buttons.
        """

        intro = QtGui.QLabel()  # see show() for where the text is initialized
        intro.setObjectName('intro')
        intro.setWordWrap(True)

        scroll = QtGui.QScrollArea()
        scroll.setObjectName('scroll')

        layout = super(BrowserStripper, self)._ui()
        layout.addWidget(intro)
        layout.addWidget(scroll)
        layout.addSpacing(self._SPACING)
        layout.addWidget(QtGui.QLabel("... and remove the following:"))

        for value, label in [
                ('ours', "only [sound] tags or paths generated by AwesomeTTS"),
                ('theirs', "only [sound] tags not generated by AwesomeTTS"),
                ('any', "all [sound] tags, regardless of origin"),
        ]:
            radio = QtGui.QRadioButton(label)
            radio.setObjectName(value)
            layout.addWidget(radio)

        layout.addWidget(self._ui_buttons())

        return layout

    # Events #################################################################

    def show(self, *args, **kwargs):
        """
        Populate the checkbox list of available fields and initialize
        the introduction message, both based on what is selected.
        """

        self._notes = [
            self._browser.mw.col.getNote(note_id)
            for note_id in self._browser.selectedNotes()
        ]

        self.findChild(QtGui.QLabel, 'intro').setText(
            "From the %d note%s selected in the Browser, scan the following "
            "fields:" %
            (len(self._notes), "s" if len(self._notes) != 1 else "")
        )

        layout = QtGui.QVBoxLayout()
        for field in sorted({field
                             for note in self._notes
                             for field in note.keys()}):
            checkbox = QtGui.QCheckBox(field)
            checkbox.attsFieldName = field
            layout.addWidget(checkbox)

        panel = QtGui.QWidget()
        panel.setLayout(layout)

        self.findChild(QtGui.QScrollArea, 'scroll').setWidget(panel)

        (
            self.findChild(
                QtGui.QRadioButton,
                self._addon.config['last_strip_mode'],
            )
            or self.findChild(QtGui.QRadioButton)  # use first if config bad
        ).setChecked(True)

        super(BrowserStripper, self).show(*args, **kwargs)

    def help_request(self):
        """
        Launch the web browser pointed at the subsection of the Browser
        page about stripping sounds.
        """

        self._launch_link('usage/removing')

    def accept(self):
        """
        Iterates over the selected notes and scans the checked fields
        for [sound] tags, stripping the ones requested by the user.
        """

        fields = [
            checkbox.attsFieldName
            for checkbox in self.findChildren(QtGui.QCheckBox)
            if checkbox.isChecked()
        ]

        if not fields:
            self._alerts("You must select at least one field.", self)
            return

        mode = next(
            radio.objectName()
            for radio in self.findChildren(QtGui.QRadioButton)
            if radio.isChecked()
        )

        # TODO iterate over _notes and update as requested

        self._addon.config['last_strip_mode'] = mode
        self._notes = None

        super(BrowserStripper, self).accept()

        # this alert is done by way of a singleShot() callback to avoid random
        # crashes on Mac OS X, which happen <5% of the time if called directly
        QtCore.QTimer.singleShot(
            0,
            lambda: self._alerts("Feature not implemented.", self._browser),
        )
