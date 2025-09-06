// Basic form validation
document.addEventListener('DOMContentLoaded', function() {
    // Add basic validation to forms
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = this.querySelectorAll('input[required], textarea[required], select[required]');
            let valid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    valid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
            
            if (!valid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });
    
    // Price input validation
    const priceInputs = document.querySelectorAll('input[type="number"][name="price"]');
    
    priceInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value < 0) {
                this.value = 0;
            }
            // Format to 2 decimal places
            this.value = parseFloat(this.value).toFixed(2);
        });
    });
    
    // Quantity input validation
    const quantityInputs = document.querySelectorAll('input[type="number"][name="quantity"]');
    
    quantityInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value < 1) {
                this.value = 1;
            }
        });
    });
    
    // Image preview for product and user forms
    const imageInputs = document.querySelectorAll('input[type="file"][accept="image/*"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    // Create or update preview image
                    let preview = input.parentNode.querySelector('.image-preview');
                    
                    if (!preview) {
                        preview = document.createElement('div');
                        preview.className = 'image-preview mt-2';
                        input.parentNode.appendChild(preview);
                    }
                    
                    preview.innerHTML = `<img src="${e.target.result}" alt="Preview" class="img-fluid" style="max-width: 200px; max-height: 200px;">`;
                };
                
                reader.readAsDataURL(file);
            }
        });
    });
});