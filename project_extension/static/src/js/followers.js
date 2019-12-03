odoo.define('project_extension.Followers', function (require) {
"use strict";

var Followers = require('mail.Followers');
var CustomFollowers = Followers.include({
    _updateSubscription: function (event, followerID, isChannel) {
        var ids = {};
        var subtypes;

        if (followerID !== undefined) {
            // Subtypes edited from the modal
            subtypes = this.dialog.$('input[type="checkbox"]');
            if (isChannel) {
                ids.channel_ids = [followerID];
            } else {
                ids.partner_ids = [followerID];
            }
        } else {
            subtypes = this.$('.o_followers_actions input[type="checkbox"]');
            ids.partner_ids = [this.partnerID];
        }

        // Get the subtype ids
        var checklist = [];
        _.each(subtypes, function (record) {
            if ($(record).is(':checked')) {
                checklist.push(parseInt($(record).data('id')));
            }
        });

        // If no more subtype followed, unsubscribe the follower
        if (!checklist.length) {
            this._unfollow(ids).fail(function () {
                $(event.currentTarget).find('input').addBack('input').prop('checked', true);
            });
        } else {
            var kwargs = _.extend({}, ids);
            if (followerID === undefined || followerID === this.partnerID) {
                //this.subtypes will only be updated if the current user
                //just added himself to the followers. We need to update
                //the subtypes manually when editing subtypes
                //for current user
                _.each(this.subtypes, function (subtype) {
                    subtype.followed = checklist.indexOf(subtype.id) > -1;
                });
            }
            kwargs.subtype_ids = checklist;
            kwargs.context = {}; // FIXME
            this._rpc({
                    model: this.model,
                    method: 'message_subscribe',
                    args: [[this.res_id]],
                    kwargs: kwargs,
                });
        }
    },
   })
return CustomFollowers;
});
