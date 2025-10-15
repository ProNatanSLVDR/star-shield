function createToast(message) {
    // Clone the template
    const element = htmx.find("[data-toast-template]").cloneNode(true)
  
    // Remove the data-toast-template attribute
    delete element.dataset.toastTemplate
  
    // Set the CSS classes based on message type
    const header = element.querySelector('.toast-header')
    const body = element.querySelector('.toast-body')
    
    let icon, title, bgClass, textClass
    
    switch(message.tags) {
        case 'error':
            icon = 'fa-circle-exclamation'
            title = 'Erreur'
            bgClass = 'bg-danger'
            textClass = 'text-white'
            break
        case 'success':
            icon = 'fa-circle-check'
            title = 'Succès'
            bgClass = 'bg-success'
            textClass = 'text-white'
            break
        case 'warning':
            icon = 'fa-triangle-exclamation'
            title = 'Attention'
            bgClass = 'bg-warning'
            textClass = 'text-dark'
            break
        case 'info':
            icon = 'fa-circle-info'
            title = 'Information'
            bgClass = 'bg-info'
            textClass = 'text-white'
            break
        default:
            icon = 'fa-bell'
            title = 'Message'
            bgClass = 'bg-primary'
            textClass = 'text-white'
    }
    
    // Apply classes
    header.classList.add(bgClass, textClass)
    element.classList.add(bgClass, textClass)
    
    // Set the title with icon
    const titleElement = element.querySelector('[data-toast-title]')
    titleElement.innerHTML = `<i class="fa-solid ${icon} me-2"></i>${title}`
    
    // Set the time
    const timeElement = element.querySelector('[data-toast-time]')
    const now = new Date()
    timeElement.textContent = now.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
  
    // Set the message
    body.textContent = message.message
  
    // Add the new element to the container
    htmx.find("[data-toast-container]").appendChild(element)
  
    // Show the toast using Bootstrap's API
    const toast = new bootstrap.Toast(element, { delay: 5000 })
    toast.show()
}