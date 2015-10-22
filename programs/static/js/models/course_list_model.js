define([
        'backbone'
    ],
    function( Backbone ) {
        'use strict';

        return Backbone.Model.extend({
            defaults: [
                {
                    name: 'Course 1',
                    id: '001'
                }, {
                    name: 'Course 2',
                    id: '002'
                }, {
                    name: 'Course 3',
                    id: '003'
                }, {
                    name: 'Course 4',
                    id: '004'
                }
            ]
        });
    }
);
