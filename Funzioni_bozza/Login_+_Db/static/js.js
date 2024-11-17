function initMap() {
    // Centra la mappa su Roma, con un livello di zoom di 12
    var roma = { lat: 41.9028, lng: 12.4964 };

    // Crea la mappa
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 12,
        center: roma
    });

    // Aggiungi un marker
    var marker = new google.maps.Marker({
        position: roma,
        map: map
    });
}
google.maps.event.addListener(map, 'click', function(event) {
    var clickedLocation = event.latLng;
    var marker = new google.maps.Marker({
        position: clickedLocation,
        map: map
    });
});
