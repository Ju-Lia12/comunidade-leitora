// Atualiza o texto para mostrar a nota que a pessoa escolheu.
const notas = document.querySelectorAll(".rating-input input");

notas.forEach((input) => {
    input.addEventListener("change", () => {
        document.querySelector(".rating-value").textContent = `${input.value} de 5 estrelas`;
    });
});
