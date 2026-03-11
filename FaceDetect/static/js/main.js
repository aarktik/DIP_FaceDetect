document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const btnHome = document.getElementById('btn-home');
    const btnHistory = document.getElementById('btn-history');
    const secHome = document.getElementById('section-home');
    const secHistory = document.getElementById('section-history');

    btnHome.addEventListener('click', () => switchTab('home'));
    btnHistory.addEventListener('click', () => {
        switchTab('history');
        loadHistory();
    });

    function switchTab(tab) {
        if (tab === 'home') {
            btnHome.classList.add('active');
            btnHistory.classList.remove('active');
            secHome.classList.add('active');
            secHistory.classList.remove('active');
        } else {
            btnHistory.classList.add('active');
            btnHome.classList.remove('active');
            secHistory.classList.add('active');
            secHome.classList.remove('active');
        }
    }

    // Upload & Drag Drop Logic
    const uploadPanel = document.getElementById('upload-panel');
    const fileInput = document.getElementById('image-input');
    const dropZone = document.getElementById('drop-zone');

    uploadPanel.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Reset button
    document.getElementById('btn-analyze-new').addEventListener('click', () => {
        document.getElementById('results-panel').classList.add('hidden');
        uploadPanel.classList.remove('hidden');
        fileInput.value = '';
    });

    // File Processing
    async function handleFileUpload(file) {
        if (!file.type.match('image.*')) {
            alert('กรุณาอัปโหลดไฟล์รูปภาพเท่านั้น');
            return;
        }

        // Show loading state
        uploadPanel.classList.add('hidden');
        document.getElementById('loading-panel').classList.remove('hidden');
        document.getElementById('results-panel').classList.add('hidden');

        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Server error');
            }

            displayResults(data);

        } catch (error) {
            alert('โหย เกิดข้อผิดพลาด: ' + error.message);
            // Revert state
            document.getElementById('loading-panel').classList.add('hidden');
            uploadPanel.classList.remove('hidden');
        }
    }

    function displayResults(data) {
        document.getElementById('loading-panel').classList.add('hidden');
        document.getElementById('results-panel').classList.remove('hidden');

        // Text stats
        document.getElementById('res-total').textContent = data.total_faces;
        document.getElementById('res-male').textContent = data.male_count;
        document.getElementById('res-female').textContent = data.female_count;

        // Imagery (cache buster added so browser gets fresh image)
        const t = new Date().getTime();
        document.getElementById('img-original').src = `${data.original_image}?t=${t}`;
        document.getElementById('img-processed').src = `${data.processed_image}?t=${t}`;

        // Download link
        document.getElementById('btn-download').href = data.processed_image;
    }

    // History Loading
    async function loadHistory() {
        const grid = document.getElementById('history-grid');
        const loader = document.getElementById('history-loader');
        
        grid.innerHTML = '';
        loader.classList.remove('hidden');

        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            
            loader.classList.add('hidden');
            
            if (data.length === 0) {
                grid.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: var(--text-muted);">ยังไม่มีประวัติการใช้งาน</p>';
                return;
            }

            data.forEach(item => {
                const date = new Date(item.timestamp + 'Z'); // UTC
                const dateStr = date.toLocaleString('th-TH');

                const card = document.createElement('div');
                card.className = 'history-card glass-panel';
                card.dataset.id = item.id;
                
                card.innerHTML = `
                    <div style="position: relative;">
                        <img src="${item.processed_image}" class="history-img" alt="History Image" loading="lazy">
                        <button class="btn-delete" data-id="${item.id}" title="ลบประวัตินี้"><i class="fa-solid fa-trash-can"></i></button>
                    </div>
                    <div class="history-info">
                        <div class="history-stats">
                            <span><i class="fa-solid fa-users" style="color: #c4b5fd;"></i> ${item.total_faces}</span>
                            <span><i class="fa-solid fa-mars" style="color: #7dd3fc;"></i> ${item.male_count}</span>
                            <span><i class="fa-solid fa-venus" style="color: #f9a8d4;"></i> ${item.female_count}</span>
                        </div>
                        <div class="history-meta mt-2">
                            <span class="history-date">${dateStr}</span>
                            <a href="${item.processed_image}" target="_blank" style="color: var(--accent-blue);"><i class="fa-solid fa-up-right-from-square"></i></a>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });

            // Add delete event listeners
            document.querySelectorAll('.btn-delete').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation(); // prevent card click if any
                    const itemId = e.currentTarget.dataset.id;
                    if (confirm('คุณต้องการลบประวัตินี้ใช่หรือไม่?')) {
                        await deleteHistory(itemId, e.currentTarget.closest('.history-card'));
                    }
                });
            });

        } catch (e) {
            loader.classList.add('hidden');
            grid.innerHTML = '<p style="text-align:center; color: red;">เกิดข้อผิดพลาดในการโหลดประวัติ</p>';
        }
    }

    async function deleteHistory(id, cardElement) {
        try {
            const res = await fetch(`/api/history/${id}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (data.success) {
                // Animate removal
                cardElement.style.transform = 'scale(0.8)';
                cardElement.style.opacity = '0';
                setTimeout(() => {
                    cardElement.remove();
                    // Check if empty
                    const grid = document.getElementById('history-grid');
                    if (grid.children.length === 0) {
                        grid.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: var(--text-muted);">ไม่มีประวัติการใช้งานแล้ว</p>';
                    }
                }, 300);
            } else {
                alert('ไม่สามารถลบได้: ' + (data.error || 'Unknown error'));
            }
        } catch (e) {
            alert('เกิดข้อผิดพลาดในการลบ: ' + e.message);
        }
    }
});
