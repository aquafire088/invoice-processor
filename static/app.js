// This script handles the frontend logic for the invoice processing application.
// It includes file upload handling, preview generation, field selection, and result display.
        document.addEventListener('DOMContentLoaded', function() {
            /* ========== DOM ELEMENT SELECTORS ========== */
            const dropzone = document.getElementById('dropzone');
            const fileInput = document.getElementById('fileInput');
            const browseBtn = document.getElementById('browseBtn');
            const extractBtn = document.getElementById('extractBtn');
            const resultsSection = document.getElementById('resultsSection');
            const resultsContainer = document.getElementById('resultsContainer');
            const lineItemsCheckbox = document.getElementById('lineItemsCheckbox');
            const lineItemOptions = document.getElementById('lineItemOptions');
            const selectAllBtn = document.getElementById('selectAllBtn');
            
            // New elements for preview section
            const invoicePreviewsContainer = document.getElementById('invoicePreviewsContainer');
            const uploadStatus = document.getElementById('uploadStatus');
            const errorMessage = document.getElementById('errorMessage');
            const progressBar = document.getElementById('progressBar');
            const progress = document.getElementById('progress');
            const fileInfo = document.getElementById('fileInfo');
            const totalFiles = document.getElementById('totalFiles');
            const totalSize = document.getElementById('totalSize');
            
            /* ========== CONFIGURATION CONSTANTS ========== */
            const commonFields = [
                'vendor_name',
                'invoice_number',
                'invoice_date',
                'due_date',
                'total_amount',
                'tax_amount',
                'line_items',
                'item_description',
                'item_quantity',
                'item_unit_price',
                'item_total'
            ];

            const VALID_FILE_TYPES = [
                'application/pdf', 
                'image/png', 
                'image/jpeg', 
                'image/jpg'
            ];

            // Track uploaded files
            let uploadedFiles = [];
            
            /* ========== EVENT LISTENERS ========== */
            lineItemsCheckbox.addEventListener('change', function() {
                lineItemOptions.style.display = this.checked ? 'block' : 'none';
            });

            dropzone.addEventListener('click', () => fileInput.click());
            browseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fileInput.click();
            });

            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.classList.add('dragover');
            });

            dropzone.addEventListener('dragleave', () => {
                dropzone.classList.remove('dragover');
            });

            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            });

            fileInput.addEventListener('change', () => {
                handleFiles(fileInput.files);
            });

            /* ========== FILE HANDLING FUNCTIONS ========== */
            function handleFiles(files) {
                try {
                    // Clear previous previews if not adding files
                    if (!fileInput.multiple || fileInput.files.length === 0) {
                        invoicePreviewsContainer.innerHTML = '';
                        uploadedFiles = [];
                    }

                    const validFiles = Array.from(files).filter(file => 
                        VALID_FILE_TYPES.includes(file.type)
                    );

                    if (validFiles.length === 0 && files.length > 0) {
                        showNotification('Please upload only PDF, PNG, or JPG files.', 'error');
                        errorMessage.style.display = 'block';
                        return;
                    } else {
                        errorMessage.style.display = 'none';
                    }

                    // Add to our files array
                    uploadedFiles = [...uploadedFiles, ...validFiles];
                    
                    // Update file info
                    updateFileInfo();
                    
                    // Update status message
                    uploadStatus.querySelector('p').textContent = 
                        uploadedFiles.length > 0 
                        ? `${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''} ready for processing` 
                        : 'No files uploaded yet.';
                    
                    // Create previews for valid files
                    validFiles.forEach(file => createInvoicePreview(file));
                    updateExtractButtonState();
                    
                } catch (error) {
                    console.error('Error handling files:', error);
                    showNotification('Error processing files. Please try again.', 'error');
                }
            }

            // Create in-page previews
            function createInvoicePreview(file) {
                const previewItem = document.createElement('div');
                previewItem.className = 'invoice-preview';
                previewItem.setAttribute('data-filename', file.name);

                if (file.type === 'application/pdf') {
                    previewItem.innerHTML = `
                        <div class="pdf-preview">
                            <div class="file-icon">📄</div>
                            <button class="remove-file" data-file="${file.name}">×</button>
                        </div>
                        <div class="file-info">${file.name}</div>
                    `;
                    
                    // Add click handler to show PDF preview
                    previewItem.addEventListener('click', (e) => {
                        if (!e.target.classList.contains('remove-file')) {
                            previewFile(file);
                        }
                    });
                    
                    // Try to render PDF thumbnail if PDF.js is available
                    if (typeof pdfjsLib !== 'undefined') {
                        const loadingTask = pdfjsLib.getDocument(URL.createObjectURL(file));
                        loadingTask.promise.then(pdf => {
                            pdf.getPage(1).then(page => {
                                const viewport = page.getViewport({ scale: 0.5 });
                                const canvas = document.createElement('canvas');
                                const context = canvas.getContext('2d');
                                canvas.height = viewport.height;
                                canvas.width = viewport.width;
                                
                                // Clear existing content
                                const previewContainer = previewItem.querySelector('.pdf-preview');
                                previewContainer.innerHTML = '';
                                previewContainer.appendChild(canvas);
                                
                                // Render the page
                                page.render({
                                    canvasContext: context,
                                    viewport: viewport
                                });
                            });
                        }).catch(error => {
                            console.error('PDF preview error:', error);
                        });
                    }
                } else {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewItem.innerHTML = `
                            <img src="${e.target.result}" alt="${file.name}">
                            <button class="remove-file" data-file="${file.name}">×</button>
                            <div class="file-info">${file.name}</div>
                        `;
                        
                        // Add click handler to show larger image preview
                        previewItem.addEventListener('click', (e) => {
                            if (!e.target.classList.contains('remove-file')) {
                                previewFile(file, e.target.src);
                            }
                        });
                    };
                    reader.readAsDataURL(file);
                }

                // Add remove functionality
                const removeBtn = previewItem.querySelector('.remove-file');
                removeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    removeFile(file.name);
                });

                invoicePreviewsContainer.appendChild(previewItem);
            }
            
            function updateFileInfo() {
                totalFiles.textContent = uploadedFiles.length;
                
                const totalBytes = uploadedFiles.reduce((total, file) => total + file.size, 0);
                const totalKB = Math.round(totalBytes / 1024);
                totalSize.textContent = totalKB < 1024 
                    ? `${totalKB} KB` 
                    : `${(totalKB / 1024).toFixed(2)} MB`;
            }

            function removeFile(filename) {
                try {
                    // Remove from file input
                    const dt = new DataTransfer();
                    Array.from(fileInput.files).forEach(file => {
                        if (file.name !== filename) dt.items.add(file);
                    });
                    fileInput.files = dt.files;
                    
                    // Remove from our files array
                    uploadedFiles = uploadedFiles.filter(file => file.name !== filename);
                    
                    // Update file info
                    updateFileInfo();
                    
                    // Update status message
                    uploadStatus.querySelector('p').textContent = 
                        uploadedFiles.length > 0 
                        ? `${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''} ready for processing` 
                        : 'No files uploaded yet.';

                    // Remove from preview section
                    document.querySelector(`.invoice-preview[data-filename="${filename}"]`)?.remove();
                    
                    updateExtractButtonState();

                } catch (error) {
                    console.error('Error removing file:', error);
                    showNotification('Error removing file. Please try again.', 'error');
                }
            }

            /* ========== PREVIEW MODAL FUNCTIONS ========== */
            function previewFile(file, imageDataUrl = null) {
                try {
                    const modal = createModal(file.name);
                    
                    if (file.type === 'application/pdf') {
                        showPdfPreview(file, modal);
                    } else {
                        showImagePreview(imageDataUrl, file.name, modal);
                    }

                    setupModalCloseHandlers(modal);
                    
                } catch (error) {
                    console.error('Error showing preview:', error);
                    showNotification('Error displaying file preview.', 'error');
                }
            }

            function createModal(filename) {
                const modal = document.createElement('div');
                modal.className = 'preview-modal';
                modal.innerHTML = `
                    <div class="preview-content">
                        <div class="preview-header">
                            <h3>${filename}</h3>
                            <button class="close-preview">&times;</button>
                        </div>
                        <div class="preview-body"></div>
                    </div>
                `;
                document.body.appendChild(modal);
                return modal;
            }

            function showPdfPreview(file, modal) {
                const pdfContainer = modal.querySelector('.preview-body');
                
                if (typeof pdfjsLib !== 'undefined') {
                    const loadingTask = pdfjsLib.getDocument(URL.createObjectURL(file));
                    loadingTask.promise.then(pdf => {
                        pdf.getPage(1).then(page => {
                            const viewport = page.getViewport({ scale: 1.0 });
                            const canvas = document.createElement('canvas');
                            const context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            
                            pdfContainer.appendChild(canvas);
                            page.render({
                                canvasContext: context,
                                viewport: viewport
                            });
                        });
                    }).catch(error => {
                        console.error('PDF.js error:', error);
                        showFallbackPdfPreview(file, pdfContainer);
                    });
                } else {
                    showFallbackPdfPreview(file, pdfContainer);
                }
            }

            function showFallbackPdfPreview(file, container) {
                container.innerHTML = `
                    <div class="pdf-fallback">
                        <div class="file-icon large">📄</div>
                        <p>${file.name}</p>
                        <a href="${URL.createObjectURL(file)}" target="_blank" class="btn">Open full PDF</a>
                    </div>
                `;
            }

            function showImagePreview(imageDataUrl, filename, modal) {
                const img = document.createElement('img');
                img.src = imageDataUrl;
                img.alt = filename;
                modal.querySelector('.preview-body').appendChild(img);
            }

            function setupModalCloseHandlers(modal) {
                modal.querySelector('.close-preview').addEventListener('click', () => {
                    modal.remove();
                });

                modal.addEventListener('click', (e) => {
                    if (e.target === modal) modal.remove();
                });

                modal.querySelector('.preview-content').addEventListener('click', (e) => {
                    e.stopPropagation();
                });
            }

            /* ========== FIELD SELECTION FUNCTIONS ========== */
            function updateExtractButtonState() {
                extractBtn.disabled = !(areFieldsSelected() && uploadedFiles.length > 0);
            }

            function areFieldsSelected() {
                return document.querySelectorAll('.field-selection input[type="checkbox"]:checked').length > 0;
            }

            selectAllBtn.addEventListener('click', function() {
                document.querySelectorAll('.field-selection input[type="checkbox"]').forEach(checkbox => {
                    checkbox.checked = commonFields.includes(checkbox.name);
                });
                
                lineItemOptions.style.display = 
                    document.querySelector('input[name="line_items"]').checked ? 'block' : 'none';
                
                updateExtractButtonState();
            });

            document.querySelectorAll('.field-selection input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', updateExtractButtonState);
            });

            /* ========== FILE UPLOAD & PROCESSING ========== */
            extractBtn.addEventListener('click', async function () {
                if (uploadedFiles.length === 0) return;

                try {
                    extractBtn.disabled = true;
                    extractBtn.innerHTML = '<span class="spinner"></span> Processing...';

                    progressBar.style.display = 'block';
                    progress.style.width = '0%';

                    const selectedFields = getSelectedFields();
                    const formData = new FormData();

                    // ✅ Append all uploaded files
                    uploadedFiles.forEach(file => {
                        formData.append("files", file);
                    });

                    // ✅ Append selected fields as JSON string
                    formData.append("fields", JSON.stringify(selectedFields));

                    // ✅ Send to your FastAPI backend
                    const response = await fetch("http://localhost:8000/process", {
                        method: "POST",
                        body: formData
                    });

                    if (!response.ok) throw new Error("Server error");

                    const results = await response.json();

                    displayResults(results);  // Your existing function to show results
                    showNotification(`${results.length} file(s) processed successfully!`, 'success');

                } catch (error) {
                    console.error('Processing error:', error);
                    showNotification('Error processing files: ' + error.message, 'error');
                } finally {
                    extractBtn.disabled = false;
                    extractBtn.textContent = 'Extract Fields';
                    progressBar.style.display = 'none';
                }
            });



            function getSelectedFields() {
                const selected = [];
                document.querySelectorAll('.field-selection input[type="checkbox"]:checked').forEach(checkbox => {
                    selected.push(checkbox.name);
                });
                return selected;
            }

            /* ========== RESULTS DISPLAY ========== */
            function displayResults(results) {
                try {
                    resultsSection.style.display = 'block';
                    resultsContainer.innerHTML = '';
                    
                    if (!results || results.length === 0) {
                        resultsContainer.innerHTML = '<div class="no-results">No results to display</div>';
                        return;
                    }

                    results.forEach((result, index) => {
                        const resultCard = createResultCard(result, index);
                        resultsContainer.appendChild(resultCard);
                    });

                    setupResultCardInteractions();
                    resultsSection.scrollIntoView({ behavior: 'smooth' });
                    
                } catch (error) {
                    console.error('Error displaying results:', error);
                    showNotification('Error displaying results.', 'error');
                }
            }

            function createResultCard(result, index) {
                const resultCard = document.createElement('div');
                resultCard.className = 'result-card';
                
                if (result.error) {
                    resultCard.innerHTML = `
                        <div class="result-header">
                            <h3>${result.fileName}</h3>
                            <span class="error">Error</span>
                        </div>
                        <div class="error-message">${result.error}</div>
                    `;
                } else {
                    resultCard.innerHTML = `
                        <div class="result-header">
                            <h3>${result.fileName}</h3>
                            <div class="result-actions">
                                <button class="action-btn copy-btn" data-target="structured-${index}">Copy JSON</button>
                                <button class="action-btn download-btn" data-filename="${result.fileName}" data-content='${JSON.stringify(result.extractedFields, null, 2)}'>Download</button>
                            </div>
                        </div>
                        <div class="result-tabs">
                            <button class="tab-btn active" data-tab="structured-${index}">Structured</button>
                            <button class="tab-btn" data-tab="raw-${index}">Raw</button>
                            <button class="tab-btn" data-tab="prompt-${index}">Prompt</button>
                        </div>
                        <div class="tab-content active" id="structured-${index}">
                            <pre>${JSON.stringify(result.extractedFields, null, 2)}</pre>
                        </div>
                        <div class="tab-content" id="raw-${index}">
                            <pre>${JSON.stringify(result.rawResponse, null, 2)}</pre>
                        </div>
                        <div class="tab-content" id="prompt-${index}">
                            <pre>${result.promptUsed || 'N/A'}</pre>
                        </div>
                    `;
                }
                
                return resultCard;
            }

            function setupResultCardInteractions() {
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const tabName = this.getAttribute('data-tab');
                        const card = this.closest('.result-card');
                        
                        card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                        this.classList.add('active');
                        
                        card.querySelectorAll('.tab-content').forEach(content => {
                            content.classList.remove('active');
                        });
                        card.querySelector(`#${tabName}`).classList.add('active');
                    });
                });

                document.querySelectorAll('.copy-btn').forEach(btn => {
                    btn.addEventListener('click', async function() {
                        try {
                            const targetId = this.getAttribute('data-target');
                            const content = document.querySelector(`#${targetId} pre`).textContent;
                            await navigator.clipboard.writeText(content);
                            
                            const originalText = this.textContent;
                            this.textContent = 'Copied!';
                            setTimeout(() => {
                                this.textContent = originalText;
                            }, 2000);
                        } catch (error) {
                            console.error('Copy failed:', error);
                            showNotification('Failed to copy to clipboard', 'error');
                        }
                    });
                });

                document.querySelectorAll('.download-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        try {
                            const filename = this.getAttribute('data-filename');
                            const content = this.getAttribute('data-content');
                            const blob = new Blob([content], { type: 'application/json' });
                            const url = URL.createObjectURL(blob);
                            
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${filename.split('.')[0]}_extracted.json`;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        } catch (error) {
                            console.error('Download failed:', error);
                            showNotification('Failed to download file', 'error');
                        }
                    });
                });
            }

            /* ========== UTILITY FUNCTIONS ========== */
            function showNotification(message, type = 'info') {
                const notification = document.createElement('div');
                notification.className = `notification ${type}`;
                notification.textContent = message;
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.classList.add('fade-out');
                    setTimeout(() => notification.remove(), 500);
                }, 5000);
            }
        });
