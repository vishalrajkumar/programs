define([
        'backbone',
        'jquery',
        'js/collections/programs_collection'
    ],
    function( Backbone, $, ProgramsCollection ) {
        'use strict';

        return Backbone.Model.extend({
            urlRoot: '/api/v1/programs/',

            initialize: function() {
                this.setHeaders();
            },

            getList: function() {
                $.ajax({
                    type: 'GET',
                    url: this.urlRoot,
                    headers: this.headers,
                    contentType: 'application/json; charset=utf-8',
                    context: this,
                    // NB: setting context fails in tests
                    success: _.bind( this.setData, this ),
                    error: function( jqXHR ) {
                        console.log( 'error: ', jqXHR );
                    }
                });
            },

            setData: function( data ) {
                this.set( data, { silent: true } );
                this.setResults( data.results );
            },

            setHeaders: function() {
                this.headers = {};
            },

            setResults: function( results ) {
                var programsCollection = new ProgramsCollection();

                programsCollection.set( results );
                this.set( { results: programsCollection }, { silent: true });
                this.trigger( 'sync', this );
            }
        });
    }
);