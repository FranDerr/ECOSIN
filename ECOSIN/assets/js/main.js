(function($) {

	var	$window = $(window),
		$body = $('body'),
		settings = {

			// Carousels
			carousels: {
				speed: 4,
				fadeIn: true,
				fadeDelay: 250
			},

		};

	// Breakpoints.
	breakpoints({
		wide:      [ '1281px',  '1680px' ],
		normal:    [ '961px',   '1280px' ],
		narrow:    [ '841px',   '960px'  ],
		narrower:  [ '737px',   '840px'  ],
		mobile:    [ null,      '736px'  ]
	});

	// Play initial animations on page load.
	$window.on('load', function() {
		window.setTimeout(function() {
			$body.removeClass('is-preload');
		}, 100);
	});

	// Dropdowns.
	$('#nav > ul').dropotron({
		mode: 'fade',
		speed: 350,
		noOpenerFade: true,
		alignment: 'center'
	});

	// Scrolly.
	$('.scrolly').scrolly();

	// Nav.

	// Button.
	$(
		'<div id="navButton">' +
		'<a href="#navPanel" class="toggle"></a>' +
		'</div>'
	)
		.appendTo($body);

	// Panel.
	$(
		'<div id="navPanel">' +
		'<nav>' +
		$('#nav').navList() +
		'</nav>' +
		'</div>'
	)
		.appendTo($body)
		.panel({
			delay: 500,
			hideOnClick: true,
			hideOnSwipe: true,
			resetScroll: true,
			resetForms: true,
			target: $body,
			visibleClass: 'navPanel-visible'
		});

	// Carousels.
	$('.carousel').each(function() {

		var	$t = $(this),
			$forward = $('<span class="forward"></span>'),
			$backward = $('<span class="backward"></span>'),
			$reel = $t.children('.reel'),
			$items = $reel.children('article');

		var	pos = 0,
			leftLimit,
			rightLimit,
			itemWidth,
			reelWidth,
			timerId;

		// Items.
		if (settings.carousels.fadeIn) {

			$items.addClass('loading');

			$t.scrollex({
				mode: 'middle',
				top: '-20vh',
				bottom: '-20vh',
				enter: function() {

					var	timerId,
						limit = $items.length - Math.ceil($window.width() / itemWidth);

					timerId = window.setInterval(function() {
						var x = $items.filter('.loading'), xf = x.first();

						if (x.length <= limit) {

							window.clearInterval(timerId);
							$items.removeClass('loading');
							return;

						}

						xf.removeClass('loading');

					}, settings.carousels.fadeDelay);

				}
			});

		}

		// Main.
		$t._update = function() {
			pos = 0;
			rightLimit = (-1 * reelWidth) + $window.width();
			leftLimit = 0;
			$t._updatePos();
		};

		$t._updatePos = function() { $reel.css('transform', 'translate(' + pos + 'px, 0)'); };

		// Forward.
		$forward
			.appendTo($t)
			.hide()
			.mouseenter(function(e) {
				timerId = window.setInterval(function() {
					pos -= settings.carousels.speed;

					if (pos <= rightLimit)
					{
						window.clearInterval(timerId);
						pos = rightLimit;
					}

					$t._updatePos();
				}, 10);
			})
			.mouseleave(function(e) {
				window.clearInterval(timerId);
			});

		// Backward.
		$backward
			.appendTo($t)
			.hide()
			.mouseenter(function(e) {
				timerId = window.setInterval(function() {
					pos += settings.carousels.speed;

					if (pos >= leftLimit) {

						window.clearInterval(timerId);
						pos = leftLimit;

					}

					$t._updatePos();
				}, 10);
			})
			.mouseleave(function(e) {
				window.clearInterval(timerId);
			});

		// Init.
		$window.on('load', function() {

			reelWidth = $reel[0].scrollWidth;

			if (browser.mobile) {

				$reel
					.css('overflow-y', 'hidden')
					.css('overflow-x', 'scroll')
					.scrollLeft(0);
				$forward.hide();
				$backward.hide();

			}
			else {

				$reel
					.css('overflow', 'visible')
					.scrollLeft(0);
				$forward.show();
				$backward.show();

			}

			$t._update();

			$window.on('resize', function() {
				reelWidth = $reel[0].scrollWidth;
				$t._update();
			}).trigger('resize');

		});

	});

})(jQuery);
function sendmail() {
	// Raccogliere i valori dai campi del modulo
	var name = $('#name').val();
	var email = $('#email').val();
	var subject = $('#Subject').val();  // Non viene utilizzato nel corpo dell'email, ma se ti serve puoi aggiungerlo
	var message = $('#message').val();

	// Validazione dei campi
	if (!name || !email || !message) {
		alert('Per favore, compila tutti i campi!');
		return; // Ferma l'esecuzione della funzione se un campo è vuoto
	}

	// Validazione dell'email
	var emailPattern = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
	if (!emailPattern.test(email)) {
		alert('Per favore, inserisci un indirizzo email valido!');
		return;
	}

	// Corpo del messaggio email
	var Body = 'Nome: ' + name + '<br>Email: ' + email + '<br>Messaggio: ' + message;

	// Invio dell'email utilizzando SMTPJS o altro servizio
	Email.send({
		SecureToken: "fbf31702-bb7f-4a4e-9c1c-4ccf17ee777f", // Il token di sicurezza
		To: 'francescoderrico@hotmail.com', // Destinatario
		From: 'mittente@example.com', // Mittente (specifica un indirizzo email valido)
		Subject: "NUOVO MESSAGGIO DA " + name,
		Body: Body
	}).then(
		message => {
			// Gestione della risposta
			if (message == 'OK') {
				alert('La tua email è stata inviata con successo!');
				// Puoi anche resettare il modulo se vuoi
				$('#name').val('');
				$('#email').val('');
				$('#message').val('');
			} else {
				console.error(message);  // Log dell'errore
				alert('C\'è stato un errore nell\'invio dell\'email. Riprova più tardi.');
			}
		}
	);
}



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


