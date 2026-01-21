let currentUser = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadUsers();
    loadProducts();
});

// Load list of users
function loadUsers() {
    fetch('/api/users')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('selectUser');
            select.innerHTML = '<option value="">-- Choose a user --</option>';
            data.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user;
                option.textContent = user;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading users:', error));
}

// Create a new user
function createUser() {
    const userInput = document.getElementById('userInput');
    const userId = userInput.value.trim();

    if (!userId) {
        alert('Please enter a user ID');
        return;
    }

    fetch('/api/add-user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            userInput.value = '';
            loadUsers();
            alert('User created successfully!');
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => console.error('Error creating user:', error));
}

// Select a user
function selectUser() {
    const select = document.getElementById('selectUser');
    currentUser = select.value;

    if (!currentUser) {
        document.getElementById('userInfo').classList.add('hidden');
        document.getElementById('purchaseHistory').innerHTML = '<p class="empty-message">Select a user to see purchase history</p>';
        document.getElementById('recommendations').innerHTML = '<p class="empty-message">Select a user and click "Get Recommendations"</p>';
        return;
    }

    document.getElementById('currentUserName').textContent = currentUser;
    document.getElementById('userInfo').classList.remove('hidden');
    loadPurchaseHistory();
}

// Load purchase history for current user
function loadPurchaseHistory() {
    if (!currentUser) return;

    fetch(`/api/user-history/${currentUser}`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('purchaseHistory');
            
            if (data.history.length === 0) {
                container.innerHTML = '<p class="empty-message">No purchases yet</p>';
                document.getElementById('purchaseCount').textContent = '0';
                return;
            }

            document.getElementById('purchaseCount').textContent = data.history.length;
            container.innerHTML = '';

            data.history.forEach(item => {
                const div = document.createElement('div');
                div.className = 'product-item';
                div.innerHTML = `
                    <div class="product-item-header">
                        <span class="sku">SKU: ${item.sku}</span>
                        <span class="price">$${item.unit_price.toFixed(2)}</span>
                    </div>
                    <div class="product-details">
                        <div><span class="detail-label">Color:</span> ${item.color}</div>
                        <div><span class="detail-label">Size:</span> ${item.size}</div>
                    </div>
                `;
                container.appendChild(div);
            });
        })
        .catch(error => console.error('Error loading purchase history:', error));
}

// Load recommendations for current user
function loadRecommendations() {
    if (!currentUser) {
        alert('Please select a user first');
        return;
    }

    const n = document.getElementById('numRecommendations').value;
    const container = document.getElementById('recommendations');
    container.innerHTML = '<p class="empty-message">Loading recommendations...</p>';

    fetch(`/api/recommendations/${currentUser}?n=${n}`)
        .then(response => response.json())
        .then(data => {
            container.innerHTML = '';

            if (data.recommendations.length === 0) {
                container.innerHTML = '<p class="empty-message">No recommendations available</p>';
                return;
            }

            data.recommendations.forEach(item => {
                const div = document.createElement('div');
                div.className = 'recommendation-item';
                
                const similarity = item.similarity !== undefined ? (item.similarity * 100).toFixed(1) : 'N/A';
                
                div.innerHTML = `
                    <div class="product-item-header">
                        <span class="sku">SKU: ${item.sku}</span>
                        <span class="price">$${item.unit_price.toFixed(2)}</span>
                    </div>
                    <div class="product-details">
                        <div><span class="detail-label">Color:</span> ${item.color}</div>
                        <div><span class="detail-label">Size:</span> ${item.size}</div>
                    </div>
                    ${similarity !== 'N/A' ? `<div class="similarity-score">Match Score: ${similarity}%</div>` : ''}
                `;
                container.appendChild(div);
            });
        })
        .catch(error => console.error('Error loading recommendations:', error));
}

// Add product to user
function addProductToUser() {
    if (!currentUser) {
        alert('Please select a user first');
        return;
    }

    const skuInput = document.getElementById('skuInput');
    const sku = skuInput.value.trim();

    if (!sku) {
        alert('Please enter a SKU');
        return;
    }

    fetch('/api/add-purchase', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: currentUser,
            sku: sku
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            skuInput.value = '';
            loadPurchaseHistory();
            alert('Product added successfully!');
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => console.error('Error adding product:', error));
}

// Load product catalog
function loadProducts() {
    fetch('/api/products')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('productCatalog');
            container.innerHTML = '';

            if (data.products.length === 0) {
                container.innerHTML = '<p class="empty-message">No products available</p>';
                return;
            }

            data.products.forEach(item => {
                const div = document.createElement('div');
                div.className = 'catalog-item';
                div.innerHTML = `
                    <div class="sku">${item.sku}</div>
                    <div class="color">${item.color}</div>
                    <div class="size">Size: ${item.size}</div>
                    <div class="price">$${item.unit_price.toFixed(2)}</div>
                `;
                div.onclick = () => {
                    document.getElementById('skuInput').value = item.sku;
                };
                container.appendChild(div);
            });
        })
        .catch(error => console.error('Error loading products:', error));
}
