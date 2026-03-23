/* Student Economy Platform — Main JavaScript */

document.addEventListener('DOMContentLoaded', function () {

    // ---- Auto-dismiss flash messages after 5 seconds ----
    const alerts = document.querySelectorAll('.alert.auto-dismiss');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // ---- Photo upload preview (listing create/edit) ----
    const photoInputs = document.querySelectorAll('.photo-input');
    photoInputs.forEach(input => {
        input.addEventListener('change', function () {
            const previewId = this.dataset.preview;
            const preview = document.getElementById(previewId);
            if (!preview) return;

            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = e => {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    preview.closest('.photo-slot')?.classList.add('has-photo');
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    // ---- Profile photo preview ----
    const profilePhotoInput = document.getElementById('id_profile_photo');
    const profilePhotoPreview = document.getElementById('profile-photo-preview');
    if (profilePhotoInput && profilePhotoPreview) {
        profilePhotoInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = e => {
                    profilePhotoPreview.src = e.target.result;
                    profilePhotoPreview.style.display = 'block';
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }

    // ---- Listing gallery thumbnail switcher ----
    const thumbnails = document.querySelectorAll('.listing-gallery .thumbnail');
    const mainPhoto = document.querySelector('.listing-gallery .main-photo');
    if (mainPhoto && thumbnails.length) {
        thumbnails.forEach(thumb => {
            thumb.addEventListener('click', function () {
                mainPhoto.src = this.dataset.full || this.src;
                thumbnails.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }

    // ---- Toggle save/wishlist (AJAX) ----
    const saveButtons = document.querySelectorAll('.btn-save-listing');
    saveButtons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const url = this.dataset.url;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || getCookie('csrftoken');

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(r => r.json())
            .then(data => {
                if (data.saved) {
                    this.innerHTML = '<i class="bi bi-bookmark-fill"></i>';
                    this.title = 'Remove from wishlist';
                    this.classList.add('text-primary');
                } else {
                    this.innerHTML = '<i class="bi bi-bookmark"></i>';
                    this.title = 'Save to wishlist';
                    this.classList.remove('text-primary');
                }
            })
            .catch(console.error);
        });
    });

    // ---- Mark notification as read (AJAX) ----
    const notifLinks = document.querySelectorAll('.notification-item[data-mark-url]');
    notifLinks.forEach(item => {
        item.addEventListener('click', function () {
            const url = this.dataset.markUrl;
            const csrfToken = getCookie('csrftoken');
            if (url) {
                fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                });
                this.classList.remove('unread');
                // Decrease badge count
                const badge = document.querySelector('.notif-count-badge');
                if (badge) {
                    let count = parseInt(badge.textContent || '0') - 1;
                    if (count <= 0) {
                        badge.remove();
                    } else {
                        badge.textContent = count;
                    }
                }
            }
        });
    });

    // ---- Chat: auto scroll to bottom ----
    const chatContainer = document.querySelector('.chat-messages');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // ---- Chat: submit on Enter (Shift+Enter for new line) ----
    const chatInput = document.querySelector('.chat-input textarea');
    if (chatInput) {
        chatInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.closest('form').submit();
            }
        });
    }

    // ---- Interactive star rating ----
    initStarRating();

    // ---- Price range slider sync ----
    const minPriceInput = document.getElementById('id_min_price');
    const maxPriceInput = document.getElementById('id_max_price');
    if (minPriceInput && maxPriceInput) {
        minPriceInput.addEventListener('input', function () {
            if (parseInt(this.value) > parseInt(maxPriceInput.value || '99999999')) {
                maxPriceInput.value = this.value;
            }
        });
    }

    // ---- Confirm delete actions ----
    const deleteForms = document.querySelectorAll('form.confirm-delete');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            const msg = this.dataset.confirmMsg || 'Are you sure you want to delete this? This action cannot be undone.';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});

function initStarRating() {
    const ratingWidget = document.querySelector('.star-rating-interactive');
    if (!ratingWidget) return;

    const stars = ratingWidget.querySelectorAll('.star-btn');
    const ratingInput = ratingWidget.querySelector('input[type="hidden"]');

    stars.forEach((star, idx) => {
        star.addEventListener('click', function () {
            const value = parseInt(this.dataset.value);
            if (ratingInput) ratingInput.value = value;
            stars.forEach((s, i) => {
                s.innerHTML = i < value
                    ? '<i class="bi bi-star-fill text-warning fs-3"></i>'
                    : '<i class="bi bi-star text-muted fs-3"></i>';
            });
        });

        star.addEventListener('mouseenter', function () {
            const value = parseInt(this.dataset.value);
            stars.forEach((s, i) => {
                s.innerHTML = i < value
                    ? '<i class="bi bi-star-fill text-warning fs-3"></i>'
                    : '<i class="bi bi-star text-muted fs-3"></i>';
            });
        });

        star.addEventListener('mouseleave', function () {
            const currentValue = parseInt(ratingInput?.value || 0);
            stars.forEach((s, i) => {
                s.innerHTML = i < currentValue
                    ? '<i class="bi bi-star-fill text-warning fs-3"></i>'
                    : '<i class="bi bi-star text-muted fs-3"></i>';
            });
        });
    });
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}
