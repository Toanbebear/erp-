odoo.define('voip.PhoneField', function (require) {
"use strict";

const basicFields = require('web.basic_fields');
const core = require('web.core');
const config = require('web.config');
const session = require('web.session');
const Phone = basicFields.FieldPhone;
const _t = core._t;

// As voip is not supported on mobile devices,
// we want to keep the standard phone widget
if (config.device.isMobile) {
    return;
}

/**
 * Override of FieldPhone to use the DialingPanel to perform calls on clicks.
 */
Phone.include({
    events: Object.assign({}, Phone.prototype.events, {
        'click': '_onClick',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Uses the DialingPanel to perform the call.
     *
     * @private
     * @param {string} number
     */
    _call(number) {
        // Có số điện thoại IP Phone caresoft mới gọi được
        if (session.cs_ip_phone){
//        this.do_notify(
//            _t("Start Calling"),
//            _.str.sprintf(_t('Calling %s'), number));
            this.trigger_up('voip_call', {
                number,
                resId: this.res_id,
                resModel: this.model,
            });
        } else{
            console.log("Chưa có số điện thoại IP Phone caresoft. Cần vào người dùng để cấu hình IP Phone");
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the phone number is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (this.mode !== 'readonly') {
            return;
        }
        ev.preventDefault();
        this._call(this.value);
        // Bật chế độ lên và gọi
//        let pbxConfiguration;
//        this.trigger_up('get_pbx_configuration', {
//            callback(output) {
//                pbxConfiguration = output.pbxConfiguration;
//            },
//        });
//        if (
//            pbxConfiguration.mode !== 'prod' ||
//            (
//                pbxConfiguration.pbx_ip &&
//                pbxConfiguration.wsServer &&
//                pbxConfiguration.login &&
//                pbxConfiguration.password
//            )
//        ) {
//            ev.preventDefault();
//            this._call(this.value);
//        }
    },
});

});
