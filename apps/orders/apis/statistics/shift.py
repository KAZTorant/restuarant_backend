from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Statistics


class CurrentShiftAPIView(APIView):
    """
    API endpoint to get current active shift information.
    
    This endpoint:
    - Recalculates till_now statistics
    - Returns current shift data if one is open
    
    Returns:
    - shift_id: ID of the current shift
    - cash_total: Total cash earned during shift
    - card_total: Total card payments during shift
    - other_total: Total other payments during shift
    - total: Grand total
    - cash_in_hand: Total cash available (initial + earned)
    - initial_cash: Starting cash amount
    - initial_card: Starting card amount
    - initial_other: Starting other payment amount
    - started_by: Username who started the shift
    - start_time: When shift was started
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Recalculate current shift statistics
        Statistics.objects.calculate_till_now(request.user)

        # Get current open shift
        shift = Statistics.objects.filter(
            started_by=request.user,
            is_closed=False,
            title='till_now'
        ).first()

        if not shift:
            return Response(
                {"error": "Aktiv növbə tapılmadı"},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            'shift_id': shift.id,
            'cash_total': str(shift.cash_total),
            'card_total': str(shift.card_total),
            'other_total': str(shift.other_total),
            'total': str(shift.total),
            'cash_in_hand': str(shift.cash_total + shift.initial_cash),
            'card_in_hand': str(shift.card_total + shift.initial_card),
            'other_in_hand': str(shift.other_total + shift.initial_other),
            'initial_cash': str(shift.initial_cash),
            'initial_card': str(shift.initial_card),
            'initial_other': str(shift.initial_other),
            'started_by': shift.started_by.username,
            'start_time': shift.start_time.isoformat() if shift.start_time else None,
            'notes': shift.notes,
        }

        return Response(data, status=status.HTTP_200_OK)


class StartShiftInfoAPIView(APIView):
    """
    API endpoint to get suggested initial amounts for starting a new shift.
    
    This endpoint returns the remaining amounts from the last closed shift,
    which can be used as initial amounts for the new shift.
    
    Returns:
    - initial_cash: Suggested starting cash (from last shift's remaining)
    - initial_card: Suggested starting card amount
    - initial_other: Suggested starting other payment amount
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get last closed shift
        last = Statistics.objects.filter(
            is_closed=True,
            title='till_now'
        ).order_by('-end_time').first()

        if not last:
            return Response({
                'initial_cash': '0.00',
                'initial_card': '0.00',
                'initial_other': '0.00',
            }, status=status.HTTP_200_OK)

        initial_cash = last.remaining_cash if last else Decimal('0.00')
        initial_card = last.remaining_card if last else Decimal('0.00')
        initial_other = last.remaining_other if last else Decimal('0.00')

        return Response({
            'initial_cash': str(initial_cash),
            'initial_card': str(initial_card),
            'initial_other': str(initial_other),
        }, status=status.HTTP_200_OK)


class StartShiftAPIView(APIView):
    """
    API endpoint to start a new shift.
    
    Request body (POST):
    - initial_cash: Starting cash amount (optional, default: 0)
    - initial_card: Starting card amount (optional, default: 0)
    - initial_other: Starting other payment amount (optional, default: 0)
    - notes: Optional notes for shift start
    
    Returns:
    - Success message with shift details
    - shift_id: ID of the newly created shift
    
    Errors:
    - 400: If there's already an open shift
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get initial amounts from request
            init_cash = Decimal(request.data.get('initial_cash', '0') or '0')
            init_card = Decimal(request.data.get('initial_card', '0') or '0')
            init_other = Decimal(request.data.get('initial_other', '0') or '0')
            notes = request.data.get('notes', '').strip()

            # Start the shift
            shift = Statistics.objects.start_shift(request.user)
            shift.initial_cash = init_cash
            shift.initial_card = init_card
            shift.initial_other = init_other
            shift.notes = notes
            shift.save()

            # Calculate initial statistics
            Statistics.objects.calculate_till_now(request.user)

            return Response({
                'message': f"Növbə açıldı (Başlanğıc: Nağd {shift.initial_cash} AZN, Kart {shift.initial_card} AZN, Digər {shift.initial_other} AZN)",
                'shift_id': shift.id,
                'initial_cash': str(shift.initial_cash),
                'initial_card': str(shift.initial_card),
                'initial_other': str(shift.initial_other),
                'start_time': shift.start_time.isoformat() if shift.start_time else None,
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class EndShiftAPIView(APIView):
    """
    API endpoint to end/close a shift.
    
    Path parameter:
    - shift_id: ID of the shift to close
    
    Request body (POST):
    - withdrawn_amount: Amount of cash withdrawn (optional, default: 0)
    - withdrawn_from_card: Amount withdrawn from card (optional, default: 0)
    - withdrawn_from_other: Amount withdrawn from other payments (optional, default: 0)
    - withdrawn_notes: Notes about the withdrawal (optional)
    
    Returns:
    - Success message with remaining amounts
    
    Errors:
    - 404: If shift not found
    - 400: If validation fails (e.g., withdrawing more than available)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, shift_id):
        try:
            shift = Statistics.objects.get(id=shift_id, title='till_now')
        except Statistics.DoesNotExist:
            return Response(
                {"error": "Növbə tapılmadı"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get withdrawal amounts
        withdrawn = Decimal(request.data.get('withdrawn_amount', '0') or '0')
        withdrawn_from_card = Decimal(request.data.get('withdrawn_from_card', '0') or '0')
        withdrawn_from_other = Decimal(request.data.get('withdrawn_from_other', '0') or '0')
        withdrawn_notes = request.data.get('withdrawn_notes', '-') or '-'

        try:
            # End the shift
            shift = Statistics.objects.end_shift(
                shift,
                request.user,
                withdrawn,
                withdrawn_from_card,
                withdrawn_from_other,
                withdrawn_notes,
            )

            total_withdrawn = withdrawn + withdrawn_from_card + withdrawn_from_other

            return Response({
                'message': f"Növbə bağlandı. Qalan nağd: {shift.remaining_cash} AZN. Ümumi çəkilən: {total_withdrawn} AZN",
                'shift_id': shift.id,
                'remaining_cash': str(shift.remaining_cash),
                'remaining_card': str(shift.remaining_card),
                'remaining_other': str(shift.remaining_other),
                'total_withdrawn': str(total_withdrawn),
                'end_time': shift.end_time.isoformat() if shift.end_time else None,
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {"error": str(e.message) if hasattr(e, 'message') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
