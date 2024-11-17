// Funzione di inizializzazione della mappa
function initMap() {
    var roma = { lat: 41.9028, lng: 12.4964 };  // Roma

    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 12,
        center: roma
    });

    var marker = new google.maps.Marker({
        position: roma,
        map: map
    });
}
