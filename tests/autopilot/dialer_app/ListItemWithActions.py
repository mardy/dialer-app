# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2013 Canonical
#
# This file is part of dialer-app.
#
# dialer-app is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

"""Dialer app autopilot custom proxy objects."""

from ubuntuuitoolkit._custom_proxy_objects import _common


class ListItemWithActions(_common.UbuntuUIToolkitCustomProxyObjectBase):

    def _drag_pointing_device_to_delete(self):
        x, y, width, height = self.globalRect
        start_x = x + (width * 0.2)
        stop_x = x + (width * 0.8)
        start_y = stop_y = y + (height // 2)

        self.pointing_device.drag(start_x, start_y, stop_x, stop_y)

    def active_action(self, action_index):
        action_margin = ((self.actionWidth / 5) * 2)
        x_offset = ((self.actionWidth + action_margin) * action_index)
        x_offset += self.actionThreshold

        x, y, width, height = self.globalRect
        start_x = x + (width * 0.5)
        stop_x = start_x - x_offset
        start_y = stop_y = y + (height // 2)

        self.pointing_device.drag(start_x, start_y, stop_x, stop_y)

class HistoryDelegate(ListItemWithActions):
    pass
