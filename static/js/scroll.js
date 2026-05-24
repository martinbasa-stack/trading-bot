
document.body.addEventListener('click', function(event) {
    const selectedElement = event.target; //Get actual element
    if(selectedElement.id.includes('nav_') ){
    const aboutSection = document.getElementById(selectedElement.value);
    aboutSection.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
    }
});