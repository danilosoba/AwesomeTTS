# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
#
# Copyright (C) 2010-2014  Anki AwesomeTTS Development Team
# Copyright (C) 2010-2012  Arthur Helfstein Fragoso
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
Service implementation for eSpeak text-to-speech engine
"""

__all__ = ['ESpeak']

from .base import Service
from .common import Trait


class ESpeak(Service):
    """
    Provides a Service-compliant implementation for eSpeak.
    """

    __slots__ = [
        '_binary',   # path to the eSpeak binary
        '_voices',   # list of installed voices as a list of tuples
    ]

    NAME = "eSpeak"

    TRAITS = [Trait.TRANSCODING]

    def __init__(self, *args, **kwargs):
        """
        Attempts to locate the eSpeak binary and read the list of voices
        from the `espeak --voices` output. If running on Windows, the
        registry will be searched to attempt to locate the eSpeak binary
        if it is not already in the path.
        """

        super(ESpeak, self).__init__(*args, **kwargs)

        self._binary = 'espeak'

        try:
            output = self.cli_output(self._binary, '--voices')

        except OSError:
            if self.IS_WINDOWS:
                self._binary = r'%s\command_line\%s.exe' % (
                    self.reg_hklm(
                        r'Software\Microsoft\Speech\Voices\Tokens\eSpeak',
                        'Path',
                    ),
                    self._binary,
                )
                output = self.cli_output(self._binary, '--voices')

            else:
                raise

        import re
        re_voice = re.compile(r'^\s*(\d+\s+)?([-\w]+)(\s+[-\w]\s+([-\w]+))?')

        self._voices = sorted([
            (
                match.group(2).lower(),

                "%s (%s)" % (match.group(4), match.group(2)) if match.group(4)
                else match.group(2),
            )
            for match in [re_voice.match(line) for line in output]
            if match and match.group(2) != 'Pty'
        ], key=lambda voice: voice[1].lower())

        if not self._voices:
            raise EnvironmentError("No usable output from `espeak --voices`")

    def desc(self):
        """
        Returns a version string, terse description, and the TTS data
        location from `espeak --version`.
        """

        return self.cli_output(self._binary, '--version').pop(0)

    def options(self):
        """
        Provides access to voice, speed, word gap, pitch, and amplitude.
        """

        return [
            dict(
                key='voice',
                label="Voice",
                values=self._voices,
                transform=lambda value: ''.join(
                    char.lower()
                    for char in str(value)
                    if char.isalpha() or char == '-'
                ),
            ),

            dict(
                key='speed',
                label="Speed",
                values=(80, 450, "wpm"),
                transform=int,
                default=175,
            ),

            dict(
                key='gap',
                label="Word Gap",
                values=(0.0, 5.0, "seconds"),
                transform=float,
                default=0.0,
            ),

            dict(
                key='pitch',
                label="Pitch",
                values=(0, 99, "%"),
                transform=int,
                default=50,
            ),

            dict(
                key='amp',
                label="Amplitude",
                values=(0, 200),
                transform=int,
                default=100,
            ),
        ]

    def run(self, text, options, path):
        """
        Checks for unicode workaround on Windows, writes a temporary
        wave file, and then transcodes to MP3.
        """

        input_file = self.path_workaround(text)
        output_wav = self.path_temp('wav')

        self.cli_call(
            [
                self._binary,
                '-v', options['voice'],
                '-s', options['speed'],
                '-g', int(options['gap'] * 100.0),
                '-p', options['pitch'],
                '-a', options['amp'],
                '-w', output_wav,
            ] + (
                ['-f', input_file] if input_file
                else ['--', text]
            )
        )

        self.cli_transcode(output_wav, path)

        self.path_unlink(input_file, output_wav)