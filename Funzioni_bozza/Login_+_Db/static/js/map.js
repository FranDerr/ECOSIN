function initMap() {
    const frattamaggiore = { lat: 40.9403, lng: 14.2907 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 14,
        center: frattamaggiore,
    });

    // Carica i dispositivi tramite API
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            data.devices.forEach(device => {
                const marker = new google.maps.Marker({
                    position: { lat: device.lat, lng: device.lng },
                    map: map,
                    title: device.nome,
                });

                // Contenuto della finestra
                const infoContent = `
          <div>
            <h3>${device.nome}</h3>
            <p>Stato: ${device.stato}</p>
            <button onclick="location.href='/product/${device._id}';" style="padding: 5px 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
              Vedi Altro
            </button>
          </div>
        `;

                const infoWindow = new google.maps.InfoWindow({
                    content: infoContent,
                });

                marker.addListener("click", () => {
                    infoWindow.open(map, marker);
                });
            });
        });
}
