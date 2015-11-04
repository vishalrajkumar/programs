define([
        'backbone',
        'jquery',
        'underscore',
        'text!templates/program_list.underscore',
        'gettext'
    ],
    function ( Backbone, $, _, ListTpl ) {
        'use strict';

        return Backbone.View.extend({
            parentEl: '.js-program-admin',

            tpl: _.template( ListTpl ),

            initialize: function() {
                this.$parentEl = $( this.parentEl );
                this.model.on( 'change:results', this.render, this );
                this.render();
            },

            render: function() {
                if ( this.model.get('count') > 0 ) {
                    this.$el.html(
                        this.tpl( {
                            programs: this.model.get('results')
                        })
                    );

                    this.$parentEl.html( this.$el );
                }
            },

            destroy: function() {
                this.undelegateEvents();
                this.remove();
            }
        });
    }
);
