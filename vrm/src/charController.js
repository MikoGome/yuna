export function setExpression(vrm, expression="neutral") {
    if(this.currentExpressionValue >= 1) {
        return;
    }
    this.currentExpressionValue += 0.005;
    vrm.expressionManager.setValue(expression, this.currentExpressionValue)
}