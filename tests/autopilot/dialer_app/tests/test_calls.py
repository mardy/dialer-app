# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
# Author: Martin Pitt <martin.pitt@ubuntu.com>
#
# This file is part of dialer-app.
#
# dialer-app is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Tests for the Dialer App using ofono-phonesim"""

from __future__ import absolute_import

import subprocess
import os
import time

from autopilot.matchers import Eventually
from testtools.matchers import Equals, NotEquals
from testtools import skipUnless

from dialer_app.tests import DialerAppTestCase

# determine whether we are running with phonesim
try:
    out = subprocess.check_output(["/usr/share/ofono/scripts/list-modems"],
                                  stderr=subprocess.PIPE)
    have_phonesim = out.startswith("[ /phonesim ]")
except CalledProcessError:
    have_phonesim = False

@skipUnless(have_phonesim,
            "this test needs to run under with-ofono-phonesim")
class TestCalls(DialerAppTestCase):
    """Tests for simulated phone calls."""

    def setUp(self):
        # provide clean history
        self.history = os.path.expanduser("~/.local/share/history-service/history.sqlite")
        if os.path.exists(self.history):
            subprocess.call(["pkill", "history-daemon"])
            os.rename(self.history, self.history + ".orig")

        super(TestCalls, self).setUp()
        self.entry = self.main_view.dialer_page.get_keypad_entry()
        self.call_button = self.main_view.dialer_page.get_call_button()
        self.hangup_button = None

        # should have an empty history at the beginning of each test
        self.history_list = self.app.select_single(objectName="historyList")
        self.assertThat(self.history_list.visible, Equals(False))
        self.assertThat(self.history_list.count, Equals(0))

        self.keys = []
        for i in range(10):
            self.keys.append(self.main_view.dialer_page.get_keypad_key(str(i)))

    def tearDown(self):
        super(TestCalls, self).tearDown()

        # ensure that there are no leftover calls in case of failed tests
        subprocess.call(["/usr/share/ofono/scripts/hangup-all"])

        # restore history
        if os.path.exists(self.history + ".orig"):
            subprocess.call(["pkill", "history-daemon"])
            os.rename(self.history + ".orig", self.history)

    def test_outgoing_noanswer(self):
        """Outgoing call to a normal number, no answer"""

        self.keypad_dial("144")
        self.wait_live_call_page("144")

        # hang up again
        self.pointing_device.click_object(self.hangup_button)
        self.assertThat(lambda: self.app.select_single(objectName="hangupButton"), Eventually(Equals(None)))

        # should switch to call log page and show call to "Unknown"
        self.assertThat(self.history_list.visible, Eventually(Equals(True)))
        self.assertThat(self.history_list.count, Equals(1))
        self.assertThat(self.history_list.select_single("Label", text="Unknown"), NotEquals(None))

    def test_outgoing_answer_local_hangup(self):
        """Outgoing call, remote answers, local hangs up"""

        # 06123xx causes accept after xx seconds
        self.keypad_dial("0612302")
        self.wait_live_call_page("0612302")

        # stop watch should start counting
        stop_watch = self.app.select_single(objectName="stopWatch")
        self.assertIn("00:0", stop_watch.elapsed)

        # should still be connected after some time
        time.sleep(3)
        self.assertIn("00:0", stop_watch.elapsed)

        # hang up
        self.pointing_device.click_object(self.hangup_button)
        self.assertThat(lambda: self.app.select_single(objectName="hangupButton"),
                        Eventually(Equals(None)))
        self.assertThat(self.history_list.visible, Eventually(Equals(True)))

    def test_outgoing_answer_remote_hangup(self):
        """Outgoing call, remote answers and hangs up"""

        # 05123xx causes immediate accept and hangup after xx seconds
        self.keypad_dial("0512303")
        self.wait_live_call_page("0512303")

        # stop watch should start counting
        stop_watch = self.app.select_single(objectName="stopWatch")
        self.assertIn("00:0", stop_watch.elapsed)

        # after remote hangs up, should switch to call log page and show call
        # to "Unknown"
        self.assertThat(lambda: self.app.select_single(objectName="hangupButton"),
                        Eventually(Equals(None)))
        self.assertThat(self.history_list.visible, Eventually(Equals(True)))
        self.assertThat(self.history_list.count, Equals(1))
        self.assertThat(self.history_list.select_single("Label", text="Unknown"),
                        NotEquals(None))

    def test_incoming(self):
        """Incoming call"""

        # magic number 199 will cause a callback from 1234567; dialing 199
        # itself will fail, so quiesce the error
        subprocess.call(["/usr/share/ofono/scripts/dial-number", "199"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # wait for incoming call, accept; it would be nicer to fake-click the
        # popup notification, but as this isn't generated by dialer-app it
        # isn't exposed to autopilot
        self.wait_for_incoming_call()
        subprocess.call(["/usr/share/ofono/scripts/answer-calls"],
                        stdout=subprocess.PIPE)

        # call back is from that number
        self.wait_live_call_page("1234567")

        # stop watch should start counting
        stop_watch = self.app.select_single(objectName="stopWatch")
        self.assertIn("00:0", stop_watch.elapsed)

        # hang up again
        self.pointing_device.click_object(self.hangup_button)
        self.assertThat(lambda: self.app.select_single(objectName="hangupButton"), Eventually(Equals(None)))

    def keypad_dial(self, number):
        """Dial given number (string) on the keypad and call"""
        for digit in number:
            self.pointing_device.click_object(self.keys[int(digit)])
        self.assertThat(self.entry.value, Eventually(Equals(number)))

        self.pointing_device.click_object(self.call_button)

    def wait_live_call_page(self, number):
        """Wait until live call page gets visible

        Sets self.hangup_button.
        """
        self.assertThat(lambda: self.app.select_single(objectName="hangupButton"), Eventually(NotEquals(None)))
        self.hangup_button = self.app.select_single(objectName="hangupButton")
        self.assertThat(self.hangup_button.visible, Eventually(Equals(True)))
        self.assertThat(self.call_button.visible, Equals(False))

        # should show called number in title page
        lcp = self.app.select_single(objectName="pageLiveCall")
        self.assertThat(lcp.title, Equals(number))

    def wait_for_incoming_call(self):
        """Wait up to 5 s for an incoming phone call"""

        timeout = 10
        while timeout >= 0:
            out = subprocess.check_output(["/usr/share/ofono/scripts/list-calls"],
                                          stderr=subprocess.PIPE)
            if "State = incoming" in out:
                break
            timeout -= 1
            time.sleep(0.5)
        else:
            self.fail("timed out waiting for incoming phonesim call")
