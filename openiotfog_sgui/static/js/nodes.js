$(document).ready(function(){
    //connect to the socket server.
    var socket = io.connect('http://' + document.domain + ':' + location.port + '/nodes');


    //receive details from server
    socket.on('control', function(msg) {
        console.log("Received number" + msg);

    });

    socket.on('nodelist', function(msg) {
        console.log("Received number" + msg);

    });

})