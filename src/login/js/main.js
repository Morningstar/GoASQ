/** 
# Copyright 2018 Morningstar Inc. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
*/

(function(){
	function ModalSignin( element ) {
		this.element = element;
		this.blocks = this.element.getElementsByClassName('js-signin-modal-block');
		this.triggers = document.getElementsByClassName('js-signin-modal-trigger');
		this.hidePassword = this.element.getElementsByClassName('js-hide-password');
		this.init();
	};

	ModalSignin.prototype.init = function() {
		var self = this;
		//open modal/switch form
		for(var i =0; i < this.triggers.length; i++) {
			(function(i){
				self.triggers[i].addEventListener('click', function(event){
					if( event.target.hasAttribute('data-signin') ) {
						event.preventDefault();
						self.showSigninForm(event.target.getAttribute('data-signin'));
						self.toggleError(document.getElementById('signin-username'), false);
						self.toggleError(document.getElementById('signin-password'), false);
					}
				});
			})(i);
		}

		//close modal
		this.element.addEventListener('click', function(event){
			if( hasClass(event.target, 'js-signin-modal') ) {
				event.preventDefault();
				removeClass(self.element, 'pk-signin-modal--is-visible');
			}
		});

		document.getElementById('signin-password').addEventListener('keyup', function(event){
			var password = event.target.value.trim();
			var humanStrength = document.getElementById('pk-strength-human');
			var strengthScore = document.getElementById('pk-strength-score');
			humanStrength.innerText = self.checkPassStrength(self, password);
     	strengthScore.innerText = self.scorePassword(password);
		});

		//close modal when clicking the esc keyboard button
		document.addEventListener('keydown', function(event){
			(event.which=='27') && removeClass(self.element, 'pk-signin-modal--is-visible');
			var userName = document.getElementById('signin-username');
			if (userName.value.trim() != ''){
				self.toggleError(userName, false);
			}
			var password = document.getElementById('signin-password');
			if (password.value.trim() != ''){
				self.toggleError(password, false);
			}
		});

		//hide/show password
		for(var i =0; i < this.hidePassword.length; i++) {
			(function(i){
				self.hidePassword[i].addEventListener('click', function(event){
					self.togglePassword(self.hidePassword[i]);
				});
			})(i);
		}

		this.blocks[0].getElementsByTagName('form')[0].addEventListener('submit', function(event){
			event.preventDefault();
			var userName = document.getElementById('signin-username');
			if (userName.value.trim() === ''){
				self.toggleError(userName, true);
			}
			var password = document.getElementById('signin-password');
			if (password.value.trim() === ''){
				self.toggleError(password, true);
			}
		});
	};

	ModalSignin.prototype.togglePassword = function(target) {
		var password = target.previousElementSibling.previousElementSibling;
		( 'password' == password.getAttribute('type') ) ? password.setAttribute('type', 'text') : password.setAttribute('type', 'password');
		target.textContent = ( 'Hide' == target.textContent ) ? 'Show' : 'Hide';
		putCursorAtEnd(password);
	}

	ModalSignin.prototype.showSigninForm = function(type) {
		// show modal if not visible
		!hasClass(this.element, 'pk-signin-modal--is-visible') && addClass(this.element, 'pk-signin-modal--is-visible');
		// show selected form
		for( var i=0; i < this.blocks.length; i++ ) {
			this.blocks[i].getAttribute('data-type') == type ? addClass(this.blocks[i], 'pk-signin-modal__block--is-selected') : removeClass(this.blocks[i], 'pk-signin-modal__block--is-selected');
		}
	};

	ModalSignin.prototype.toggleError = function(input, bool) {
		// used to show error messages in the form
		toggleClass(input, 'pk-signin-modal__input--has-error', bool);
		toggleClass(input.nextElementSibling, 'pk-signin-modal__error--is-visible', bool);
	}

	ModalSignin.prototype.scorePassword = function(pass) {
    var score = 0;
    if (!pass)
        return score;
    // award every unique letter until 5 repetitions
    var letters = new Object();
    for (var i=0; i<pass.length; i++) {
        letters[pass[i]] = (letters[pass[i]] || 0) + 1;
        score += 5.0 / letters[pass[i]];
    }
    // bonus points for mixing it up
    var variations = {
        digits: /\d/.test(pass),
        lower: /[a-z]/.test(pass),
        symbols: /[./<>?;:"'`!@#$%^&*()\[\]{}_+=|\\-]/.test(pass),
        nonRepeating: /(?!.*([A-Za-z0-9])\1{4})/.test(pass),
        minLength: /^[a-zA-Z0-9./<>?;:"'`!@#$%^&*()\[\]{}_+=|\\-]{8,}$/.test(pass),
        upper: /[A-Z]/.test(pass),
        nonWords: /\W/.test(pass),
    }
    variationCount = 0;
    for (var check in variations) {
        variationCount += (variations[check] == true) ? 1 : 0;
    }
    score += (variationCount - 1) * 3;
    return parseInt(score);
	};
	
	ModalSignin.prototype.checkPassStrength = function(self, pass) {
    var score = self.scorePassword(pass);
    if (score > 80)
        return "strong";
    if (score > 60)
        return "good";
    if (score >= 30)
        return "weak";
    return "";
	}

	var signinModal = document.getElementsByClassName("js-signin-modal")[0];
	if( signinModal ) {
		new ModalSignin(signinModal);
	}

	//class manipulations - needed if classList is not supported
	function hasClass(el, className) {
	  	if (el.classList) return el.classList.contains(className);
	  	else return !!el.className.match(new RegExp('(\\s|^)' + className + '(\\s|$)'));
	}
	function addClass(el, className) {
		var classList = className.split(' ');
	 	if (el.classList) el.classList.add(classList[0]);
	 	else if (!hasClass(el, classList[0])) el.className += " " + classList[0];
	 	if (classList.length > 1) addClass(el, classList.slice(1).join(' '));
	}
	function removeClass(el, className) {
		var classList = className.split(' ');
	  	if (el.classList) el.classList.remove(classList[0]);	
	  	else if(hasClass(el, classList[0])) {
	  		var reg = new RegExp('(\\s|^)' + classList[0] + '(\\s|$)');
	  		el.className=el.className.replace(reg, ' ');
	  	}
	  	if (classList.length > 1) removeClass(el, classList.slice(1).join(' '));
	}
	function toggleClass(el, className, bool) {
		if(bool) addClass(el, className);
		else removeClass(el, className);
	}

	function putCursorAtEnd(el) {
    	if (el.setSelectionRange) {
      		var len = el.value.length * 2;
      		el.focus();
      		el.setSelectionRange(len, len);
    	} else {
      		el.value = el.value;
    	}
	};
})();
