// Universal Subtitles, universalsubtitles.org
// 
// Copyright (C) 2010 Participatory Culture Foundation
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
// 
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see 
// http://www.gnu.org/licenses/agpl-3.0.html.

goog.provide('mirosubs.widget.SubtitleController');

/**
 * @constructor
 */
mirosubs.widget.SubtitleController = function(
    videoID, videoURL, playController, videoTab, dropDown) 
{
    this.videoID_ = videoID;
    this.videoURL_ = videoURL;
    this.videoTab_ = videoTab;
    this.dropDown_ = dropDown;
    this.playController_ = playController;
    this.playController_.setSubtitleController(this);
    this.handler_ = new goog.events.EventHandler(this);
    this.dialogOpener_ = new mirosubs.widget.SubtitleDialogOpener(
        videoID, videoURL, this.playController_.getVideoSource(),
        function(loading) {
            if (loading)
                videoTab.showLoading();
            else
                videoTab.stopLoading();
        },
        goog.bind(playController.stopForDialog, playController));
    this.handler_.listenOnce(
        this.dialogOpener_,
        goog.ui.Dialog.EventType.AFTER_HIDE,
        this.subtitleDialogClosed_);
    var s = mirosubs.widget.DropDown.Selection;
    this.handler_.
        listen(
            dropDown,
            s.ADD_LANGUAGE,
            this.openNewLanguageDialog).
        listen(
            dropDown,
            s.IMPROVE_SUBTITLES,
            this.openSubtitleDialog).
        listen(
            videoTab.getAnchorElem(), 'click',
            this.videoAnchorClicked_
        );
};

mirosubs.widget.SubtitleController.prototype.videoAnchorClicked_ = 
    function(e) 
{
    mirosubs.Tracker.getInstance().track('videoTabClicked');
    if (!this.dropDown_.hasSubtitles())
        this.openSubtitleDialog();
    else
        this.dropDown_.toggleShow();
    e.preventDefault();
};

/**
 * Corresponds to "Add new subs" or "Improve these subs" in menu.
 * @param type {string} opt_intitial_lang= When on Improve these subs,
 *  we should now which lang to default to on the started dialog
 */
mirosubs.widget.SubtitleController.prototype.openSubtitleDialog = 
    function(e) 
{
     this.openNewLanguageDialog(this.playController_.getSubtitleState().LANGUAGE);
};

mirosubs.widget.SubtitleController.prototype.openNewLanguageDialog = 
    function(opt_intitialLang) 
{
    this.dialogOpener_.showStartDialog(
        this.playController_.getVideoSource().getVideoURL(), opt_intitialLang);
};

mirosubs.widget.SubtitleController.prototype.subtitleDialogClosed_ = function(e) {
    var dropDownContents = e.target.getDropDownContents();
    this.playController_.dialogClosed();
    this.videoTab_.showContent(
        this.dropDown_.hasSubtitles(),
        this.playController_.getSubtitleState());
    this.dropDown_.setCurrentSubtitleState(
        this.playController_.getSubtitleState());
    if (dropDownContents != null) {
        this.dropDown_.updateContents(dropDownContents);
    }
};
