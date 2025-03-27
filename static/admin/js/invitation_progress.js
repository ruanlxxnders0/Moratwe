(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Create modal HTML
        const modalHtml = `
            <div id="invitation-progress-modal" class="invitation-progress-modal" style="display:none;">
                <div class="modal-content">
                    <h2>Sending Invitations</h2>
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress" style="width: 0%"></div>
                        </div>
                        <div class="progress-text">0%</div>
                    </div>
                    <p class="status-text">
                        Sent <span class="emails-sent">0</span> of <span class="total-emails">0</span> invitations
                    </p>
                </div>
            </div>
        `;
        
        // Add modal to page
        $('body').append(modalHtml);
        
        // Add styles
        const styles = `
            .invitation-progress-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .modal-content {
                background: white;
                padding: 20px;
                border-radius: 5px;
                min-width: 300px;
            }
            .progress-container {
                margin: 20px 0;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #f0f0f0;
                border-radius: 10px;
                overflow: hidden;
            }
            .progress {
                height: 100%;
                background: #79aec8;
                transition: width 0.3s ease;
            }
            .progress-text {
                text-align: center;
                margin-top: 5px;
            }
            .status-text {
                text-align: center;
            }
        `;
        
        $('<style>').text(styles).appendTo('head');
        
        // Function to update progress
        function updateProgress(taskId) {
            $.get('/admin/events/event/send-invitations-status/' + taskId + '/', function(data) {
                if (data.type === 'update_progress') {
                    // Update progress bar
                    var progress = Math.round(data.progress);
                    var message = 'Sending invitations: ' + progress + '% (' + data.emails_sent + '/' + data.total + ')';
                    
                    // Show any failed emails
                    if (data.failed && data.failed.length > 0) {
                        message += '\nFailed emails: ' + data.failed.length;
                    }
                    
                    // Update the message
                    $('.invitation-progress').text(message);
                    
                    // Continue checking if not complete
                    if (progress < 100) {
                        setTimeout(function() {
                            updateProgress(taskId);
                        }, 1000);
                    } else if (data.type === 'complete') {
                        $('.invitation-progress').text('Invitations sent successfully!');
                    } else if (data.type === 'error') {
                        $('.invitation-progress').text('Error sending invitations: ' + data.error);
                    }
                }
            });
        }
        
        // Handle click on progress link
        $('.invitation-progress').click(function(e) {
            e.preventDefault();
            var taskId = $(this).data('task-id');
            updateProgress(taskId);
        });
    });
})(django.jQuery); 