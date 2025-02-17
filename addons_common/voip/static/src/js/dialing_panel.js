odoo.define('voip.DialingPanel', function (require) {
"use strict";

const PhoneCallActivitiesTab = require('voip.PhoneCallActivitiesTab');
const PhoneCallContactsTab = require('voip.PhoneCallContactsTab');
const PhoneCallRecentTab = require('voip.PhoneCallRecentTab');
const UserAgent = require('voip.UserAgent');

const core = require('web.core');
const config = require('web.config');
const realSession = require('web.session');
const Widget = require('web.Widget');
const Dialog = require('web.Dialog');
const _t = core._t;
const HEIGHT_OPEN = '480px';
const HEIGHT_FOLDED = '0px';
const YOUR_ARE_ALREADY_IN_A_CALL = _t("You are already in a call");

// As voip is not supported on mobile devices,
// we want to keep the standard phone widget
if (config.device.isMobile) {
    return;
}

const DialingPanel = Widget.extend({
    template: 'voip.DialingPanel',
    events: {
        'click .o_dial_enable_button': '_onClickEnableButton',
        'click .o_dial_ear_phone_button': '_onClickEarPhoneButton',
        'click .o_dial_transfer_button': '_onClickTransferButton',
        'click .o_dial_change_status_button': '_onClickChangeCallStatusButton',
        'click .o_dial_online_button': '_onClickChangeCallStatusButton',
        'click .o_dial_offline_button': '_onClickChangeCallStatusButton',
        'click .o_dial_accept_button': '_onClickAcceptButton',
        'click .o_dial_call_button': '_onClickCallButton',
        'click .o_dial_end_call_button': '_onClickEndCallButton',
        'click .o_dial_fold': '_onClickFold',
        'click .o_dial_hangup_button': '_onClickHangupButton',
        'click .o_dial_keypad_backspace': '_onClickKeypadBackspace',
        'click .o_dial_postpone_button': '_onClickPostponeButton',
        'click .o_dial_reject_button': '_onClickRejectButton',
        'click .o_dial_tabs .o_dial_tab': '_onClickTab',
        'click .o_dial_keypad_icon': '_onClickDialKeypadIcon',
        'click .o_dial_number': '_onClickDialNumber',
        'click .o_dial_window_close': '_onClickWindowClose',
        'input .o_dial_search_input': '_onInputSearch',
    },
    custom_events: {
        'changeStatus': '_onChangeStatus',
        'incomingCall': '_onIncomingCall',
        'muteCall': '_onMuteCall',
        'showHangupButton': '_onShowHangupButton',
        'sip_accepted': '_onSipAccepted',
        'sip_bye': '_onSipBye',
        'sip_cancel_incoming': '_onSipCancelIncoming',
        'sip_cancel_outgoing': '_onSipCancelOutgoing',
        'sip_customer_unavailable': '_onSipCustomerUnavailable',
        'sip_error': '_onSipError',
        'sip_error_resolved': '_onSipErrorResolved',
        'sip_incoming_call': '_onSipIncomingCall',
        'sip_rejected': '_onSipRejected',
        'switch_keypad': '_onSwitchKeypad',
        'unmuteCall': '_onUnmuteCall',
        'onClickEnableButton' : '_onClickEnableButton'
    },
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.title = _t("VOICE");
        this._isFolded = false;
        this._isInCall = false;
        this._isPostpone = false;
        this._isShow = false;
        this._onInputSearch = _.debounce(this._onInputSearch.bind(this), 500);
        this._tabs = {
            contacts: new PhoneCallContactsTab(this),
            nextActivities: new PhoneCallActivitiesTab(this),
            recent: new PhoneCallRecentTab(this),
        };
//        console.log('init  new UserAgent(this)');
        this._userAgent = new UserAgent(this);
        this.phone = false;
//        console.log('init DialingPanel');
        this.encrypt_phone = realSession.encrypt_phone;
    },
    /**
     * @override
     */
    async start() {
    console.log('start DialingPanel');
        this._$callButton = this.$('.o_dial_call_button');
        this._$endcallButton = this.$('.o_dial_end_call_button');
        this._$incomingCallButtons = this.$('.o_dial_incoming_buttons');
        this._$keypad = this.$('.o_dial_keypad');
        this._$keypadInput = this.$('.o_dial_keypad_input');
        this._$keypadInputDiv = this.$('.o_dial_keypad_input_div');
        this._$mainButtons = this.$('.o_dial_main_buttons');
        this._$postponeButton = this.$('.o_dial_postpone_button');
        this._$searchBar = this.$('.o_dial_searchbar');
        this._$searchInput = this.$('.o_dial_search_input');
        this._$tabsPanel = this.$('.o_dial_panel');
        this._$tabs = this.$('.o_dial_tabs');

        this._activeTab = this._tabs.recent;
        await this._tabs.contacts.appendTo(this.$('.o_dial_contacts'));
        await this._tabs.nextActivities.appendTo(this.$('.o_dial_next_activities'));
        await this._tabs.recent.appendTo(this.$('.o_dial_recent'));

        this.$el.css('bottom', 0);
        this.$el.hide();
        this._$incomingCallButtons.hide();
        this._$keypad.hide();

        core.bus.on('transfer_call', this, this._onTransferCall);
        core.bus.on('voip_onToggleDisplay', this, this._onToggleDisplay);

        this.call('bus_service', 'onNotification', this, this._onLongpollingNotifications);

        for (const tab of Object.values(this._tabs)) {
//            tab.on('callNumber', this, ev => csCallout(ev.data.number));
            tab.on('callNumber', this, function(ev){
                var result = csCallout(ev.data.number);
                if (result == 'OK'){
                    // Mã hóa số điện thoại
                    var maskPhone;
                    if (this.encrypt_phone == 'True'){
                        maskPhone = this.maskPhoneNumber(ev.data.number);
                    } else{
                        maskPhone = ev.data.number;
                    }
                    this.do_notify(
                        "Chuyển cuộc gọi sang máy IP Phone",
                        _.str.sprintf('Đang gọi %s', maskPhone));
                }else{
                    if (result){
                        this.do_notify(result);
                        alert(result);
                    }
                }
            });
            tab.on('hidePanelHeader', this, () => this._hideHeader());
            tab.on('showPanelHeader', this, () => this._showHeader());
        }

        // Chuyển luôn sang máy bàn
        //await this._onClickCallButton();
//        this.phone = ev.data.number;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Function called when a phonenumber is clicked in the activity widget.
     *
     * @param {Object} params
     * @param {string} params.number
     * @param {integer} params.activityId
     * @return {Promise}
     */
//    async callFromActivityWidget(params) {
//        if (!this._isInCall) {
//            this.$(`
//                .o_dial_tab.active,
//                .tab-pane.active`
//            ).removeClass('active');
//            this.$(`
//                .o_dial_activities_tab .o_dial_tab,
//                .tab-pane.o_dial_next_activities`
//            ).addClass('active');
//            this._activeTab = this._tabs.nextActivities;
//            await this._activeTab.callFromActivityWidget(params);
//            return this._makeCall(params.number);
//        } else {
//            this.do_notify(YOUR_ARE_ALREADY_IN_A_CALL);
//        }
//    },
    /**
     * Function called when widget phone is clicked.
     *
     * @param {Object} params
     * @param {string} params.number
     * @param {string} params.resModel
     * @param {integer} params.resId
     * @return {Promise}
     */
    async callFromPhoneWidget(params) {
//        console.log('callFromPhoneWidget DialingPanel');
//        console.log(params);
        // Nếu không có token và số điện thoại thì không click được
        if (params && params.number){
            // Lưu số điện thoại lại
            //params.number
            // Lưu vào giao diện
            this._$keypadInput.val(params.number);
//            if (!this._isInCall) {
                this.$(`.o_dial_tab.active, .tab-pane.active`).removeClass('active');
                this.$(`.o_dial_recent_tab .o_dial_tab, .tab-pane.o_dial_recent`).addClass('active');
                this._activeTab = this._tabs.recent;
                const phoneCall = await this._activeTab.callFromPhoneWidget(params);
                return this._makeCall(params.number);
//            } else {
//                this.do_notify(YOUR_ARE_ALREADY_IN_A_CALL);
//            }
        }
    },
    /**
     * Function called when a phone number is clicked
     *
     * @return {Object}
     */
    getPbxConfiguration() {
        return this._userAgent.getPbxConfiguration();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Block the VOIP widget
     *
     * @private
     * @param {string} message  The message we want to show when blocking the
     *   voip widget
     */
    _blockOverlay(message) {
        this._$tabsPanel.block({ message });
        this._$mainButtons.block();
    },
    /**
     * @private
     */
    _cancelCall() {
        this._isInCall = false;
        this._isPostpone = false;
        this._hidePostponeButton();
        this._showCallButton();
        this._resetMainButton();
    },
    /**
     * @private
     */
    _fold() {
        this.$el.animate({
            height: this._isFolded ? HEIGHT_FOLDED : HEIGHT_OPEN,
        });
        if (this._isFolded) {
            this.$('.o_dial_fold').css("bottom", "25px");
            this.$('.o_dial_window_close').hide();
            this.$('.o_dial_main_buttons').hide();
            this.$('.o_dial_incoming_buttons').hide();
            this.$('.o_dial_unfold').show();
        } else {
            this.$('.o_dial_fold').css("bottom", 0);
            this.$('.o_dial_window_close').show();
            this.$('.o_dial_main_buttons').show();
            this.$('.o_dial_unfold').hide();
        }
    },
    /**
     * Hides the search input and the tabs.
     *
     * @private
     */
    _hideHeader() {
        this._$searchBar.hide();
        this._$tabs.hide();
    },
    /**
     * @private
     */
    _hidePostponeButton() {
        this._$postponeButton.css('visibility', 'hidden');
    },
    /**
     * @private
     * @param {string} number
     * @param {voip.PhonenCall} [phoneCall] if the event function already created a
     *   phonecall; this phonecall is passed to the initPhoneCall function in
     *   order to not create a new one.
     * @return {Promise}
     */
    async _makeCall(number) {
        if (!this._isInCall) {
            if (!number) {
                this.do_notify(
                    _t("The phonecall has no number"),
                    _t("Please check if a phone number is given for the current phonecall"));
                return;
            }
            if (!this._isShow || this._isFolded) {
                await this._toggleDisplay();
            }
//            await this._activeTab.initPhoneCall(phoneCall);
            this._userAgent.makeCall(number);

            //csCallout(number);
            this._isInCall = true;
        } else {
            this.do_notify(YOUR_ARE_ALREADY_IN_A_CALL);
        }
    },
    /**
     * Refreshes the phonecall list of the active tab.
     *
     * @private
     * @return {Promise}
     */
    async _refreshPhoneCallsStatus() {
        console.log('_refreshPhoneCallsStatus.....');
        this._isInCall = false;
        if (this._isInCall) {
            return;
        }
        console.log(this._activeTab);
        return this._activeTab.refreshPhonecallsStatus();
    },
    /**
     * @private
     */
    _resetMainButton() {
        this._$mainButtons.show();
        this._$incomingCallButtons.hide();
    },
    /**
     * @private
     */
    _showCallButton() {
        this._$callButton.addClass('o_dial_call_button');
        this._$callButton.removeClass('o_dial_hangup_button');
    },
    /**
     * @private
     */
    _showHangupButton() {
        this._$callButton.removeClass('o_dial_call_button');
        this._$callButton.addClass('o_dial_hangup_button');
    },
    /**
     * Shows the search input and the tabs.
     *
     * @private
     */
    _showHeader() {
        this._$searchBar.show();
        this._$tabs.show();
    },
    /**
     * @private
     */
    _showPostponeButton() {
        this._$postponeButton.css('visibility', 'visible');
    },
    /**
     * @private
     * @return {Promise}
     */
    async _showWidget() {
        if (!this._isShow) {
            this.$el.show();
            this._isShow = true;
            this._isFolded = false;
            this._$searchInput.focus();
        }
        if (this._isFolded) {
            return this._toggleFold({ isFolded: false });
        }
    },
    /**
     * @private
     * @return {Promise}
     */
    async _toggleDisplay() {
        if (this._isShow) {
            if (!this._isFolded) {
                this.$el.hide();
                this._isShow = false;
            } else {
                return this._toggleFold({ isFolded: false });
            }
        } else {
            this.$el.show();
            this._isShow = true;
            this._isFolded = false;
            this._$searchInput.focus();
        }
    },
    /**
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.isFolded]
     * @return {Promise}
     */
    async _toggleFold({ isFolded }={}) {
        if (!config.device.isMobile) {
            if (this._isFolded) {
                await this._refreshPhoneCallsStatus();
            }
            this._isFolded = _.isBoolean(isFolded) ? isFolded : !this._isFolded;
            this._fold();
        } else {
            this._onToggleDisplay();
        }
    },
    /**
     * @private
     */
    _toggleKeypadInputDiv() {
        if (this._isInCall) {
            this._$keypadInputDiv.hide();
        } else {
            this._$keypadInputDiv.show();
            this._$keypadInput.focus();
        }
    },
    /**
     * Unblock the VOIP widget
     *
     * @private
     */
    _unblockOverlay() {
        this._$tabsPanel.unblock();
        this._$mainButtons.unblock();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChangeStatus() {
        this._activeTab.changeRinging();
    },
    /**
     * @private
     */
    _onClickAcceptButton() {
        this._userAgent.acceptIncomingCall();
        this._$mainButtons.show();
        this._$incomingCallButtons.hide();
    },

    _onClickEnableButton() {
        try {
            csEnableCall();
        }catch(e){
            const content = `Cấu hình IP Phone Caresoft chưa chính xác. Vui lòng liên hệ phòng IT để được hỗ trợ.`;
            new Dialog(this, {
                    size: 'medium',
                    title: "Thông báo",
                    $content: $('<div>'+content+'</div>'),
                    buttons: [{
                        text: _t("Đóng"),
                        close: true,
                    }],
                }).open();
        }
//        this._userAgent.acceptIncomingCall();
//        this._$mainButtons.show();
//        this._$incomingCallButtons.hide();
    },

    _onClickEarPhoneButton() {
        $(".o_dial_ear_phone_button i.fa-headphones").css("color", "green");
        $(".o_dial_transfer_button i.fa-fax").css("color", "gray");
        try {
            changeDevice(1);
        }catch(e){
            const content = `Cấu hình IP Phone Caresoft chưa chính xác. Vui lòng liên hệ phòng IT để được hỗ trợ.`;
            new Dialog(this, {
                    size: 'medium',
                    title: "Thông báo",
                    $content: $('<div>'+content+'</div>'),
                    buttons: [{
                        text: _t("Đóng"),
                        close: true,
                    }],
                }).open();
        }

//        this._userAgent.acceptIncomingCall();
//        this._$mainButtons.show();
//        this._$incomingCallButtons.hide();


    },

    _onClickTransferButton() {
        $(".o_dial_transfer_button i.fa-fax").css("color", "green");
        $(".o_dial_ear_phone_button i.fa-headphones").css("color", "gray");
        try {
            changeDevice(2);
        }catch(e){
            const content = `Cấu hình IP Phone Caresoft chưa chính xác. Vui lòng liên hệ phòng IT để được hỗ trợ.`;
            new Dialog(this, {
                    size: 'medium',
                    title: "Thông báo",
                    $content: $('<div>'+content+'</div>'),
                    buttons: [{
                        text: _t("Đóng"),
                        close: true,
                    }],
                }).open();
        }

//        this._userAgent.acceptIncomingCall();
//        this._$mainButtons.show();
//        this._$incomingCallButtons.hide();

    },

    _onClickChangeCallStatusButton(e) {
        // Đổi trạng thái
        var status = changeCallStatus();
//        console.log('result');
//        console.log(result);


        if (status === 'Online'){
            $(".o_dial_change_status_button i.fa-circle").css("color", "green");
        } else {
            $(".o_dial_change_status_button i.fa-circle ").css("color", "gray");
        }
        console.log('Đổi lại Ip Phone');

//changeDevice(2);
//        if($(e.currentTarget).hasClass("o_dial_online_button")){
//            $(".o_dial_change_status_button").hide();
//            $(e.currentTarget).show();
//        }else if ($(e.currentTarget).hasClass("o_dial_offline_button")){
//            $(".o_dial_online_button").hide();
//            $(e.currentTarget).show();
//        }
//        this._userAgent.acceptIncomingCall();
//        this._$mainButtons.show();
//        this._$incomingCallButtons.hide();
    },


    /**
     * Method handeling the click on the call button.
     * If a phonecall detail is displayed, then call its first number.
     * If there is a search value, we call it.
     * If we are on the keypad and there is a value, we call it.
     *
     * @private
     * @return {Promise}
     */
    async _onClickCallButton() {
        // Cho phép cuộc gọi luôn
        //_onClickTransferButton
        const number = this._$keypadInput.val();
//        console.log('number');
//        console.log(number);
//        console.log(ev.data.number);
        // Dùng IP Phone
//reConfigDeviceType();
// TODO cập nhật
        var result = csCallout(number);
        if (result == 'OK'){
            // Mã hóa số điện thoại

            try {
                var maskPhone;

                if (this.encrypt_phone == 'True'){
                    maskPhone = this.maskPhoneNumber(number);
                } else{
                    maskPhone = number;
                }
                this.do_notify(
                    "Chuyển cuộc gọi sang máy IP Phone",
                    _.str.sprintf('Đang gọi %s', maskPhone));

                // Bật nút hủy, ẩn nút gọi
                this._$callButton.addClass('o_hidden');
                this._$endcallButton.removeClass('o_hidden');
            }catch(e){
                const content = `Cấu hình IP Phone Caresoft chưa chính xác. Vui lòng liên hệ phòng IT để được hỗ trợ.`;
                new Dialog(this, {
                        size: 'medium',
                        title: "Thông báo",
                        $content: $('<div>'+content+'</div>'),
                        buttons: [{
                            text: _t("Đóng"),
                            close: true,
                        }],
                    }).open();
            }



        }else{
            if (result){
                this.do_notify(result);
                alert(result);
            }

        }

//        if (this._isInCall) {
//            return;
//        }
//        if (this.$('.o_phonecall_details').is(':visible')) {
//            this._activeTab.callFirstNumber();
//            if (this._activeTab.isAutoCallMode) {
//                this._showPostponeButton(); //TODO xdo, should be triggered from tab
//            }
//            return;
//        } else if (this._$tabsPanel.is(':visible')) {
//            return this._activeTab.callFromTab();
//        } else {
//            const number = this._$keypadInput.val();
//            if (!number) {
//                return;
//            }
//            this._onToggleKeypad();
//            this.$(`
//                .o_dial_tab.active,
//                .tab-pane.active`
//            ).removeClass('active');
//            this.$(`
//                .o_dial_recent_tab .o_dial_tab,
//                .tab-pane.o_dial_recent`
//            ).addClass('active');
//            this._activeTab = this._tabs.recent;
////            const phoneCall = await this._activeTab.callFromNumber(number);
//            await this._makeCall(number);
//            this._$keypadInput.val("");
//        }
    },

    async _onClickEndCallButton() {
        // Kết thúc cuộc gọi
        endCall();
//        csEndCall();endedCall();
        // Bật nút gọi, ẩn nút hủy
        this._$endcallButton.addClass('o_hidden');
        this._$callButton.removeClass('o_hidden');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDialKeypadIcon(ev) {
        ev.preventDefault();
        this._onToggleKeypad();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDialNumber(ev) {
        ev.preventDefault();
        this._onKeypadButtonClick(ev.currentTarget.textContent);
    },
    /**
     * @private
     * @return {Promise}
     */
    async _onClickFold() {
        return this._toggleFold();
    },
    /**
     * @private
     */
    _onClickHangupButton() {
        this._userAgent.hangup();
    },
    /**
     * @private
     */
    _onClickKeypadBackspace() {
        if (this._isInCall) {
            return;
        }
        this._$keypadInput.val(this._$keypadInput.val().slice(0, -1));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPostponeButton(ev) {
        if (!this._isInCall) {
            return;
        }
        this._isPostpone = true;
        this._userAgent.hangup();
    },
    /**
     * @private
     */
    _onClickRejectButton() {
        this._userAgent.rejectIncomingCall();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickTab(ev) {
        ev.preventDefault();
        this._activeTab = this._tabs[ev.currentTarget.getAttribute('aria-controls')];
        this._$searchInput.val("");
        return this._refreshPhoneCallsStatus();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickWindowClose(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._onToggleDisplay();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data contains the number and the partnerId of the caller.
     * @param {string} ev.data.number
     * @param {integer} ev.data.partnerId
     * @return {Promise}
     */
    async _onIncomingCall(ev) {
        await this._showWidget();
        this.$(`
            .o_dial_tab.active,
            .tab-pane.active`
        ).removeClass('active');
        this.$(`
            .o_dial_recent_tab .o_dial_tab,
            .tab-pane.o_dial_recent`
        ).addClass('active');
        this._activeTab = this._tabs.recent;
        await this._activeTab.onIncomingCall(ev.data);
        this._$mainButtons.hide();
        this._$incomingCallButtons.show();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @return {Promise}
     */
    _onInputSearch(ev) {
        return this._activeTab.searchPhoneCall($(ev.currentTarget).val());
    },
    /**
     * @private
     * @param {string} number the keypad number clicked
     */
    _onKeypadButtonClick(number) {
        if (this._isInCall) {
            this._userAgent.sendDtmf(number);
        } else {
            this._$keypadInput.val(this._$keypadInput.val() + number);
        }
    },
    /**
     * @private
     * @param {Object[]} notifications
     * @param {string} [notifications[i].type]
     */
    async _onLongpollingNotifications(notifications) {
        for (const notification of notifications) {
            if (notification[1].type === 'refresh_voip') {
                if (this._isInCall) {
                    return;
                }
                if (this._activeTab === this._tabs.nextActivities) {
                    await this._activeTab.refreshPhonecallsStatus();
                }
            }
        }
    },
    /**
     * @private
     */
    _onMuteCall() {
        this._userAgent.muteCall();
    },
    /**
     * @private
     */
    async _onNotificationRefreshVoip() {
        if (this._isInCall) {
            return;
        }
        if (this._activeTab !== this._tabs.nextActivities) {
            return;
        }
        return this._activeTab.refreshPhonecallsStatus();
    },
    /**
     * @private
     */
    _onShowHangupButton() {
        this._showHangupButton();
    },
    /**
     * @private
     */
    _onSipAccepted() {
        console.log('_onSipAccepted');
        this._activeTab.onCallAccepted();
    },
    /**
     * @private
     */
    async _onSipBye() {
        this._isInCall = false;
        this._showCallButton();
        this._hidePostponeButton();
        const isDone = !this._isPostpone;
        this._isPostpone = false;
        return this._activeTab.hangupPhonecall(isDone);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {OdooEvent} ev.data contains the number and the partnerId of the caller
     * @param {string} ev.data.number
     * @param {integer} ev.data.partnerId
     * @return {Promise}
     */
    _onSipCancelIncoming(ev) {
        this._isInCall = false;
        this._isPostpone = false;
        this._hidePostponeButton();
        this._showCallButton();
        this._resetMainButton();
        return this._activeTab.onMissedCall(ev.data);
    },
    /**
     * @private
     */
    _onSipCancelOutgoing() {
        this._cancelCall();
        this._activeTab.onCancelOutgoingCall();
    },
    /**
     * @private
     */
    _onSipCustomerUnavailable() {
        this.do_notify(
            _t("Customer unavailable"),
            _t("The customer is temporary unavailable. Please try later."));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {boolean} [ev.data.isConnecting] is true if voip is trying to
     *   connect and the error message must not disappear
     * @param {Object} ev.data.isTemporary it we want to block voip temporarly
     *   to display an error message
     * @param {Object} ev.data.message contains the message to display on the
     *   gray overlay
     */
    _onSipError(ev) {
        console.log('_onSipError');
        console.log(ev);
        const message = ev.data.message;
        this._isInCall = false;
        this._isPostpone = false;
        this._hidePostponeButton();
        console.log(ev.data);
        if (ev.data.isConnecting) {
            this._blockOverlay(message);
        } else if (ev.data.isTemporary) {
            this._blockOverlay(message);
            this.$('.blockOverlay').on('click', () => this._onSipErrorResolved());
            this.$('.blockOverlay').attr('title', _t("Click to unblock"));
        } else {
            this._blockOverlay(message);
        }
    },
    /**
     * @private
     */
    _onSipErrorResolved() {
        this._unblockOverlay();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {OdooEvent} ev.data contains the number and the partnerId of the caller
     * @param {string} ev.data.number
     * @param {integer} ev.data.partnerId
     * @return {Promise}
     */
    async _onSipIncomingCall(ev) {
        this._onSipErrorResolved();
        if (this._isInCall) {
            return;
        }
        this._isInCall = true;
        this.$(`
            .o_dial_tab.active,
            .tab-pane.active`
        ).removeClass('active');
        this.$(`
            .o_dial_recent_tab .o_dial_tab,
            .tab-pane.o_dial_recent`
        ).addClass('active');
        this._activeTab = this._tabs.recent;
        await this._activeTab.onIncomingCallAccepted(ev.data);
        this._showHangupButton();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data contains the number and the partnerId of the caller.
     * @param {string} ev.data.number
     * @param {integer} ev.data.partnerId
     * @return {Promise}
     */
    _onSipRejected(ev) {
        this._cancelCall();
        return this._activeTab.onRejectedCall(ev.data);
    },
    /**
     * @private
     */
    _onSwitchKeypad() {
        this._$keypadInput.val(this._$searchInput.val());
        this._onToggleKeypad();
    },
    /**
     * @private
     */
    async _onToggleDisplay() {
        console.log('_onToggleDisplay');
        await this._toggleDisplay();
        return this._refreshPhoneCallsStatus();
    },
    /**
     * @private
     */
    _onToggleKeypad() {
        if (this._$tabsPanel.is(":visible")) {
            this._$tabsPanel.hide();
            this._$keypad.show();
            this._toggleKeypadInputDiv();
        } else {
            this._$tabsPanel.show();
            this._$keypad.hide();
        }
    },
    /**
     * @private
     * @param {string} number
     */
    _onTransferCall(number) {
        this._userAgent.transfer(number);
    },
    /**
     * @private
     */
    _onUnmuteCall() {
        this._userAgent.unmuteCall();
    },

    maskPhoneNumber: function (phoneNumber) {
      // Kiểm tra xem số điện thoại có đủ 10 chữ số không
      if (phoneNumber.length >= 10) {
        // Sử dụng phép cắt để lấy 4 số cuối
        var lastFourDigits = phoneNumber.slice(5);

        // Tạo chuỗi "xxxxx" có độ dài bằng với 5 số cuối
        var mask = "x".repeat(lastFourDigits.length);

        // Thay thế 4 số cuối bằng chuỗi "xxxx"
        var maskedNumber = phoneNumber.slice(0, 5) + mask;

        return maskedNumber;
      } else {
        // Trả về số điện thoại không thay đổi nếu không đủ 10 chữ số
        return phoneNumber;
      }
    }
});

return DialingPanel;

});
