
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




// Funzione per alternare la visibilità della password (se utilizzata)
function togglePassword() {
    const passwordInput = document.getElementById("password");
    const passwordType = passwordInput.getAttribute("type") === "password" ? "text" : "password";
    passwordInput.setAttribute("type", passwordType);
}
